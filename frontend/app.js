/**
 * Frontend application for Speed Climbing Biomechanical Analysis
 */

const API_BASE_URL = 'http://localhost:8000/api';

let currentVideoId = null;
let powerChart = null;
let currentHolds = [];  // List of [x, y] coordinates
let finishHoldIndex = null;  // Index of the hold that marks the finish
let firstFrameImage = null;
let canvas = null;
let ctx = null;
let imageWidth = 0;
let imageHeight = 0;
let roiMode = false;  // true = selecting ROI, false = adding holds
let roiStart = null;  // {x, y} when starting ROI selection
let currentRoi = null;  // {x, y, width, height} in original image coordinates

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.addEventListener('click', handleUpload);
});

/**
 * Handle video upload and analysis
 */
async function handleUpload() {
    const fileInput = document.getElementById('videoFile');
    const weightInput = document.getElementById('climberWeight');
    const uploadStatus = document.getElementById('uploadStatus');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showStatus(uploadStatus, 'Por favor selecciona un archivo de video', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const climberWeight = parseFloat(weightInput.value) || 70.0;
    
    try {
        showLoading(true);
        showStatus(uploadStatus, 'Subiendo video...', 'info');
        
        // Step 1: Upload video
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('Error al subir el video');
        }
        
        const uploadData = await uploadResponse.json();
        currentVideoId = uploadData.video_id;
        
        showStatus(uploadStatus, 'Video subido. Configurando detección de presas...', 'info');
        
        // Step 2: Show hold detection modal
        await showHoldDetectionModal(currentVideoId, climberWeight, file);
        
    } catch (error) {
        console.error('Error:', error);
        showStatus(uploadStatus, `Error: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Display analysis results
 */
async function displayResults(analysisData, originalFile, overlayUrl) {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.classList.remove('hidden');
    
    // Display metrics
    displayMetrics(analysisData);
    
    // Display power chart
    displayPowerChart(analysisData.power_curve);
    
    // Display last hold reached
    displayLastHoldReached(analysisData);
    
    // Display videos (await since it's async)
    await displayVideos(originalFile, overlayUrl);
    
    // Display steps
    displaySteps(analysisData.steps);
}

/**
 * Display last hold reached information
 */
function displayLastHoldReached(analysisData) {
    // Remove existing last hold info if present
    const existingInfo = document.getElementById('lastHoldReachedInfo');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    if (analysisData.last_hold_reached !== null && analysisData.last_hold_reached !== undefined) {
        const resultsSection = document.getElementById('resultsSection');
        const lastHoldInfo = document.createElement('div');
        lastHoldInfo.id = 'lastHoldReachedInfo';
        lastHoldInfo.className = 'bg-yellow-600 rounded-lg p-6 mb-6';
        
        // Determine completion status
        const lastHoldNum = analysisData.last_hold_reached + 1;
        const finishHoldIndex = analysisData.finish_hold_index;
        const finishHoldNum = finishHoldIndex !== null && finishHoldIndex !== undefined 
            ? finishHoldIndex + 1 
            : null;
        
        // Debug logging
        console.log('Last hold reached info:', {
            last_hold_reached: analysisData.last_hold_reached,
            lastHoldNum: lastHoldNum,
            finish_hold_index: finishHoldIndex,
            finishHoldNum: finishHoldNum
        });
        
        let statusMessage = '';
        if (finishHoldNum !== null && finishHoldIndex !== null && finishHoldIndex !== undefined) {
            // Compare with finish hold
            const completed = analysisData.last_hold_reached >= finishHoldIndex;
            console.log('Completion check:', {
                last_hold_reached: analysisData.last_hold_reached,
                finish_hold_index: finishHoldIndex,
                comparison: `${analysisData.last_hold_reached} >= ${finishHoldIndex}`,
                result: completed
            });
            statusMessage = completed
                ? '<p class="text-green-200 mt-2">✓ Completado - Llegó a la presa final</p>'
                : `<p class="text-yellow-200 mt-2">⚠ No completó - Llegó hasta la presa ${lastHoldNum}, pero la presa final es la ${finishHoldNum}</p>`;
        } else {
            // No finish hold defined
            statusMessage = `<p class="text-gray-200 mt-2">ℹ No se ha definido una presa final</p>`;
        }
        
        lastHoldInfo.innerHTML = `
            <h3 class="text-lg font-semibold mb-2">Última Presa Alcanzada</h3>
            <p class="text-xl font-bold">Presa ${lastHoldNum}</p>
            ${statusMessage}
        `;
        // Insert after metrics table, before power chart
        const powerChartDiv = document.querySelector('#powerChart').closest('.bg-gray-800');
        resultsSection.insertBefore(lastHoldInfo, powerChartDiv);
    }
}

/**
 * Display performance metrics
 */
function displayMetrics(data) {
    const tableBody = document.getElementById('metricsTable');
    tableBody.innerHTML = '';
    
    const metrics = [
        { label: 'Tiempo de Reacción', value: `${data.reaction_time.toFixed(3)}s`, unit: '' },
        { label: 'Tiempo Total', value: `${data.total_time.toFixed(3)}s`, unit: '' },
        { label: 'Duración Total', value: `${data.total_duration.toFixed(3)}s`, unit: '' },
        { label: 'FPS del Video', value: data.fps.toFixed(2), unit: '' },
        { label: 'Número de Frames', value: data.frame_count, unit: '' },
        { label: 'Número de Pasos', value: data.steps.length, unit: '' },
        { label: 'Peso del Escalador', value: `${data.climber_weight}`, unit: 'kg' }
    ];
    
    metrics.forEach(metric => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-700';
        row.innerHTML = `
            <td class="px-4 py-2 font-medium">${metric.label}</td>
            <td class="px-4 py-2">${metric.value} ${metric.unit}</td>
        `;
        tableBody.appendChild(row);
    });
}

/**
 * Display power curve chart
 */
function displayPowerChart(powerCurve) {
    const ctx = document.getElementById('powerChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (powerChart) {
        powerChart.destroy();
    }
    
    // Check if power curve is by step or by time
    const isByStep = powerCurve.length > 0 && 'step' in powerCurve[0];
    
    if (isByStep) {
        // Power curve by step
        const steps = powerCurve.map(point => `Paso ${point.step}`);
        const powers = powerCurve.map(point => point.power);
        
        powerChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: steps,
                datasets: [{
                    label: 'Potencia Promedio (W)',
                    data: powers,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Potencia Promedio (W)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Paso'
                        }
                    }
                }
            }
        });
    } else {
        // Power curve by time (legacy)
        const times = powerCurve.map(point => point.time);
        const powers = powerCurve.map(point => point.power);
        
        powerChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: times,
                datasets: [{
                    label: 'Potencia (W)',
                    data: powers,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        labels: {
                            color: 'white'
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Tiempo (s)',
                            color: 'white'
                        },
                        ticks: {
                            color: 'white'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Potencia (W)',
                            color: 'white'
                        },
                        ticks: {
                            color: 'white'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
}

/**
 * Display video players
 */
async function displayVideos(originalFile, overlayUrl) {
    const originalVideo = document.getElementById('originalVideo');
    const analyzedVideo = document.getElementById('analyzedVideo');
    
    // Set original video
    originalVideo.src = URL.createObjectURL(originalFile);
    originalVideo.load();
    
    // Load analyzed video with proper error handling
    try {
        console.log('Intentando cargar video desde:', overlayUrl);
        
        // Fetch the video as a blob
        const response = await fetch(overlayUrl);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Error loading video: ${response.status} ${response.statusText} - ${errorText}`);
        }
        
        const blob = await response.blob();
        console.log('Video descargado, tamaño:', blob.size, 'tipo:', blob.type);
        
        if (blob.size === 0) {
            throw new Error('El archivo de video está vacío');
        }
        
        const videoBlobUrl = URL.createObjectURL(blob);
        analyzedVideo.src = videoBlobUrl;
        
        // Set error handler before loading
        analyzedVideo.onerror = (e) => {
            console.error('Error del elemento video:', e);
            console.error('Error code:', analyzedVideo.error);
            if (analyzedVideo.error) {
                console.error('Error code:', analyzedVideo.error.code);
                console.error('Error message:', analyzedVideo.error.message);
            }
            
            // Show error message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'text-red-500 p-4 text-center';
            errorMsg.innerHTML = `
                <p>Error al cargar el video analizado</p>
                <p class="text-sm">Código: ${analyzedVideo.error?.code || 'Desconocido'}</p>
                <p class="text-sm">El video puede estar en un formato no compatible. Intenta recargar la página y subir el video nuevamente.</p>
            `;
            analyzedVideo.parentNode.insertBefore(errorMsg, analyzedVideo);
        };
        
        analyzedVideo.onloadeddata = () => {
            console.log('Video analizado cargado correctamente');
        };
        
        analyzedVideo.oncanplay = () => {
            console.log('Video listo para reproducir');
        };
        
        analyzedVideo.load();
        
    } catch (error) {
        console.error('Error al obtener el video analizado:', error);
        const errorMsg = document.createElement('div');
        errorMsg.className = 'text-red-500 p-4 text-center';
        errorMsg.innerHTML = `<p>Error: ${error.message}</p>`;
        analyzedVideo.parentNode.insertBefore(errorMsg, analyzedVideo);
    }
}

/**
 * Display steps analysis
 */
function displaySteps(steps) {
    const tableBody = document.getElementById('stepsTable');
    tableBody.innerHTML = '';
    
    if (steps.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4" class="px-4 py-2 text-center text-gray-400">No se detectaron pasos</td>';
        tableBody.appendChild(row);
        return;
    }
    
    steps.forEach(step => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-700';
        row.innerHTML = `
            <td class="px-4 py-2">${step.step_number}</td>
            <td class="px-4 py-2">${step.start_time.toFixed(3)}s</td>
            <td class="px-4 py-2">${step.end_time.toFixed(3)}s</td>
            <td class="px-4 py-2">${step.duration.toFixed(3)}s</td>
        `;
        tableBody.appendChild(row);
    });
}

/**
 * Show status message
 */
function showStatus(element, message, type) {
    element.classList.remove('hidden');
    element.className = `mt-4 p-4 rounded-lg ${
        type === 'error' ? 'bg-red-600' : 
        type === 'success' ? 'bg-green-600' : 
        'bg-blue-600'
    }`;
    element.textContent = message;
}

/**
 * Show/hide loading spinner
 */
function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (show) {
        spinner.classList.remove('hidden');
    } else {
        spinner.classList.add('hidden');
    }
}

/**
 * Show hold detection modal and load first frame
 */
async function showHoldDetectionModal(videoId, climberWeight, originalFile) {
    const modal = document.getElementById('holdDetectionModal');
    modal.classList.remove('hidden');
    
    // Reset state
    currentHolds = [];
    currentRoi = null;
    roiMode = false;
    roiStart = null;
    
    // Reset UI
    const useRoiCheckbox = document.getElementById('useRoiCheckbox');
    if (useRoiCheckbox) {
        useRoiCheckbox.checked = false;
    }
    roiMode = false;
    updateRoiInfo();
    updateCanvasMode();
    
    try {
        // Load first frame
        const frameResponse = await fetch(`${API_BASE_URL}/first-frame/${videoId}`);
        if (!frameResponse.ok) {
            throw new Error('Error al cargar el primer frame');
        }
        
        const frameData = await frameResponse.json();
        imageWidth = frameData.width;
        imageHeight = frameData.height;
        
        // Create image and wait for it to load
        firstFrameImage = new Image();
        firstFrameImage.crossOrigin = 'anonymous'; // Allow cross-origin if needed
        
        firstFrameImage.onload = () => {
            console.log('First frame loaded:', imageWidth, 'x', imageHeight);
            console.log('Image natural size:', firstFrameImage.naturalWidth, 'x', firstFrameImage.naturalHeight);
            
            // Ensure we have valid dimensions
            if (imageWidth === 0 || imageHeight === 0) {
                imageWidth = firstFrameImage.naturalWidth || 640;
                imageHeight = firstFrameImage.naturalHeight || 480;
                console.log('Using image natural dimensions:', imageWidth, 'x', imageHeight);
            }
            
            setupCanvas();
            setupHSVSliders();
            setupHoldDetectionButtons(videoId, climberWeight, originalFile);
            // Initial detection with default values (this will call drawHoldsOnCanvas)
            detectHoldsWithThresholds(videoId);
        };
        
        firstFrameImage.onerror = (error) => {
            console.error('Error loading image:', error);
            console.error('Image src was:', frameData.frame.substring(0, 100) + '...');
            alert('Error al cargar la imagen del primer frame. Ver consola para más detalles.');
        };
        
        // Set src after setting up event handlers
        console.log('Setting image src, frame data:', {
            hasFrame: !!frameData.frame,
            frameLength: frameData.frame ? frameData.frame.length : 0,
            width: imageWidth,
            height: imageHeight
        });
        firstFrameImage.src = frameData.frame;
    } catch (error) {
        console.error('Error loading first frame:', error);
        alert('Error al cargar el primer frame: ' + error.message);
    }
}

/**
 * Setup canvas for drawing
 */
function setupCanvas() {
    canvas = document.getElementById('holdCanvas');
    if (!canvas) {
        console.error('Canvas element not found');
        return;
    }
    
    ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2d context');
        return;
    }
    
    // Set canvas size to image size (internal resolution)
    canvas.width = imageWidth;
    canvas.height = imageHeight;
    
    // Set display size (CSS) - maintain aspect ratio but fit container
    const container = canvas.parentElement;
    const maxWidth = container ? container.clientWidth - 20 : 800; // Leave some padding
    const aspectRatio = imageHeight / imageWidth;
    
    if (imageWidth > maxWidth) {
        canvas.style.width = maxWidth + 'px';
        canvas.style.height = (maxWidth * aspectRatio) + 'px';
    } else {
        canvas.style.width = imageWidth + 'px';
        canvas.style.height = imageHeight + 'px';
    }
    
    console.log('Canvas setup:', {
        internalSize: `${canvas.width}x${canvas.height}`,
        displaySize: `${canvas.style.width}x${canvas.style.height}`,
        imageSize: `${imageWidth}x${imageHeight}`
    });
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw image - ensure it's loaded
    if (firstFrameImage && firstFrameImage.complete && firstFrameImage.naturalWidth > 0) {
        console.log('Drawing image to canvas:', imageWidth, 'x', imageHeight);
        ctx.drawImage(firstFrameImage, 0, 0, imageWidth, imageHeight);
        // Draw overlays after image is drawn
        drawOverlays();
    } else {
        console.warn('Image not ready yet, will retry');
        // Try again after a short delay
        setTimeout(() => {
            if (firstFrameImage && firstFrameImage.complete && firstFrameImage.naturalWidth > 0) {
                console.log('Retrying to draw image');
                ctx.drawImage(firstFrameImage, 0, 0, imageWidth, imageHeight);
                drawOverlays();
            } else {
                console.error('Image still not ready after retry');
            }
        }, 200);
    }
    
    // Remove old event listeners if they exist (to avoid duplicates)
    canvas.removeEventListener('mousedown', handleCanvasMouseDown);
    canvas.removeEventListener('mousemove', handleCanvasMouseMove);
    canvas.removeEventListener('mouseup', handleCanvasMouseUp);
    canvas.removeEventListener('click', handleCanvasClick);
    canvas.removeEventListener('dblclick', handleCanvasDoubleClick);
    
    // Add event listeners for ROI and hold selection
    canvas.addEventListener('mousedown', handleCanvasMouseDown);
    canvas.addEventListener('mousemove', handleCanvasMouseMove);
    canvas.addEventListener('mouseup', handleCanvasMouseUp);
    canvas.addEventListener('click', handleCanvasClick);
    canvas.addEventListener('dblclick', handleCanvasDoubleClick);
    
    // Initialize ROI mode
    roiMode = false;
    currentRoi = null;
    roiStart = null;
    updateCanvasMode();
}

/**
 * Get canvas coordinates from mouse event
 */
function getCanvasCoordinates(event) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: Math.round((event.clientX - rect.left) * scaleX),
        y: Math.round((event.clientY - rect.top) * scaleY)
    };
}

/**
 * Setup HSV sliders
 */
function setupHSVSliders() {
    const sliders = [
        'h1Min', 'h1Max', 's1Min', 's1Max', 'v1Min', 'v1Max',
        'h2Min', 'h2Max', 's2Min', 's2Max', 'v2Min', 'v2Max',
        'minArea'
    ];
    
    sliders.forEach(sliderId => {
        const slider = document.getElementById(sliderId);
        const valueSpan = document.getElementById(sliderId + 'Value');
        
        if (slider && valueSpan) {
            slider.addEventListener('input', (e) => {
                valueSpan.textContent = e.target.value;
                // Auto-detect on slider change (debounced)
                clearTimeout(window.detectTimeout);
                window.detectTimeout = setTimeout(() => {
                    detectHoldsWithThresholds(currentVideoId);
                }, 300);
            });
        }
    });
}

/**
 * Setup hold detection buttons
 */
function setupHoldDetectionButtons(videoId, climberWeight, originalFile) {
    document.getElementById('detectHoldsBtn').addEventListener('click', () => {
        detectHoldsWithThresholds(videoId);
    });
    
    document.getElementById('confirmHoldsBtn').addEventListener('click', async () => {
        await confirmAndAnalyze(videoId, climberWeight, originalFile);
    });
    
    document.getElementById('clearHoldsBtn').addEventListener('click', () => {
        currentHolds = [];
        finishHoldIndex = null;
        drawHoldsOnCanvas();
    });
    
    document.getElementById('removeLastHoldBtn').addEventListener('click', () => {
        if (currentHolds.length > 0) {
            const removedIndex = currentHolds.length - 1;
            currentHolds.pop();
            // Adjust finish index if needed
            if (finishHoldIndex === removedIndex) {
                finishHoldIndex = null;
            } else if (finishHoldIndex !== null && finishHoldIndex > removedIndex) {
                finishHoldIndex--;
            }
            drawHoldsOnCanvas();
        }
    });
    
    
    // ROI checkbox - activates ROI mode directly
    const useRoiCheckbox = document.getElementById('useRoiCheckbox');
    if (useRoiCheckbox) {
        useRoiCheckbox.addEventListener('change', (e) => {
            roiMode = e.target.checked;
            if (!e.target.checked) {
                currentRoi = null;
                drawHoldsOnCanvas();
            }
            updateCanvasMode();
            updateRoiInfo();
        });
    }
}

/**
 * Detect holds with current HSV thresholds
 */
async function detectHoldsWithThresholds(videoId) {
    try {
        const hsv1 = {
            lower: [
                parseInt(document.getElementById('h1Min').value),
                parseInt(document.getElementById('s1Min').value),
                parseInt(document.getElementById('v1Min').value)
            ],
            upper: [
                parseInt(document.getElementById('h1Max').value),
                parseInt(document.getElementById('s1Max').value),
                parseInt(document.getElementById('v1Max').value)
            ]
        };
        
        const hsv2 = {
            lower: [
                parseInt(document.getElementById('h2Min').value),
                parseInt(document.getElementById('s2Min').value),
                parseInt(document.getElementById('v2Min').value)
            ],
            upper: [
                parseInt(document.getElementById('h2Max').value),
                parseInt(document.getElementById('s2Max').value),
                parseInt(document.getElementById('v2Max').value)
            ]
        };
        
        const minArea = parseInt(document.getElementById('minArea').value);
        
        const response = await fetch(`${API_BASE_URL}/detect-holds/${videoId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                lower_hsv1: hsv1.lower,
                upper_hsv1: hsv1.upper,
                lower_hsv2: hsv2.lower,
                upper_hsv2: hsv2.upper,
                min_area: minArea
            })
        });
        
        if (!response.ok) {
            throw new Error('Error al detectar presas');
        }
        
        const data = await response.json();
        currentHolds = data.holds || [];
        console.log('Holds detected:', currentHolds.length, currentHolds);
        drawHoldsOnCanvas();
    } catch (error) {
        console.error('Error detecting holds:', error);
    }
}

/**
 * Draw holds on canvas
 */
function drawHoldsOnCanvas() {
    if (!canvas || !ctx || !firstFrameImage) {
        console.error('Canvas, context, or image not available');
        return;
    }
    
    // Clear canvas first
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Redraw image - ensure it's loaded
    if (firstFrameImage.complete && firstFrameImage.naturalWidth > 0) {
        ctx.drawImage(firstFrameImage, 0, 0, imageWidth, imageHeight);
    } else {
        console.warn('Image not ready, waiting...');
        // If image isn't ready, wait a bit and try again
        setTimeout(() => {
            if (firstFrameImage.complete) {
                ctx.drawImage(firstFrameImage, 0, 0, imageWidth, imageHeight);
                drawOverlays();
            }
        }, 50);
        return;
    }
    
    drawOverlays();
}

/**
 * Draw overlays (ROI and holds) on canvas
 */
function drawOverlays() {
    if (!ctx) {
        console.error('Canvas context not available in drawOverlays');
        return;
    }
    
    console.log('Drawing overlays - ROI:', currentRoi, 'Holds:', currentHolds ? currentHolds.length : 0);
    
    // Draw ROI if exists - only border, no fill
    if (currentRoi) {
        ctx.strokeStyle = 'yellow';
        ctx.lineWidth = 3;
        ctx.setLineDash([]); // Solid line
        ctx.strokeRect(currentRoi.x, currentRoi.y, currentRoi.width, currentRoi.height);
        
        // Draw ROI label
        ctx.fillStyle = 'yellow';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText('ROI', currentRoi.x + 5, currentRoi.y + 5);
    }
    
    // Draw holds
    if (!currentHolds || currentHolds.length === 0) {
        console.log('No holds to draw');
    }
    (currentHolds || []).forEach((hold, index) => {
        const [x, y] = hold;
        const isFinishHold = finishHoldIndex === index;
        
        // Draw circle - different color for finish hold
        // Check if hold is being touched (for video overlay, this would be checked per frame)
        // For canvas preview, we just show the finish hold color
        if (isFinishHold) {
            // Finish hold: purple/violet with gold border (different from red and green)
            ctx.fillStyle = 'rgba(138, 43, 226, 0.8)'; // BlueViolet color
        } else {
            // Regular hold: red
            ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
        }
        ctx.beginPath();
        ctx.arc(x, y, 15, 0, 2 * Math.PI);
        ctx.fill();
        
        // Draw border - thicker for finish hold
        if (isFinishHold) {
            ctx.strokeStyle = '#FFD700'; // Gold color
            ctx.lineWidth = 4;
        } else {
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 2;
        }
        ctx.stroke();
        
        // Draw number
        ctx.fillStyle = 'white';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText((index + 1).toString(), x, y);
        
        // Draw "FIN" label for finish hold
        if (isFinishHold) {
            ctx.fillStyle = '#FFD700'; // Gold color
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText('FIN', x, y + 20);
        }
    });
    
    // Update count
    const roiInfo = currentRoi ? ` | ROI: ${currentRoi.width}x${currentRoi.height}` : '';
    const finishInfo = finishHoldIndex !== null ? ` | Presa FIN: ${finishHoldIndex + 1}` : '';
    const holdsCountEl = document.getElementById('holdsCount');
    if (holdsCountEl) {
        holdsCountEl.textContent = `Presas detectadas: ${currentHolds.length}${roiInfo}${finishInfo}`;
    }
}

/**
 * Handle canvas mouse down (for ROI selection)
 */
function handleCanvasMouseDown(event) {
    if (!roiMode) return;
    
    const coords = getCanvasCoordinates(event);
    roiStart = { x: coords.x, y: coords.y };
    canvas.style.cursor = 'crosshair';
}

/**
 * Handle canvas mouse move (for ROI selection)
 */
function handleCanvasMouseMove(event) {
    if (!roiMode || !roiStart) return;
    
    const coords = getCanvasCoordinates(event);
    
    // Draw temporary ROI
    drawHoldsOnCanvas();
    
    // Draw temporary ROI rectangle - only border, no fill
    ctx.strokeStyle = 'yellow';
    ctx.lineWidth = 3;
    ctx.setLineDash([5, 5]); // Dashed line while dragging
    const width = coords.x - roiStart.x;
    const height = coords.y - roiStart.y;
    ctx.strokeRect(roiStart.x, roiStart.y, width, height);
    ctx.setLineDash([]);
}

/**
 * Handle canvas mouse up (finish ROI selection)
 */
function handleCanvasMouseUp(event) {
    if (!roiMode || !roiStart) return;
    
    const coords = getCanvasCoordinates(event);
    
    // Calculate ROI
    const x = Math.min(roiStart.x, coords.x);
    const y = Math.min(roiStart.y, coords.y);
    const width = Math.abs(coords.x - roiStart.x);
    const height = Math.abs(coords.y - roiStart.y);
    
    // Only set ROI if it's large enough (at least 100x100 pixels)
    if (width > 100 && height > 100) {
        currentRoi = { x, y, width, height };
        console.log('ROI seleccionada:', currentRoi);
    } else {
        currentRoi = null;
        alert('ROI demasiado pequeña. Selecciona un área de al menos 100x100 píxeles.');
    }
    
    roiStart = null;
    drawHoldsOnCanvas();
    updateRoiInfo();
    updateCanvasMode();
}

/**
 * Handle canvas click to add/remove hold manually (only when not in ROI mode)
 */
function handleCanvasClick(event) {
    if (roiMode) return; // ROI mode handles clicks differently
    
    const coords = getCanvasCoordinates(event);
    const x = coords.x;
    const y = coords.y;
    
    // Check if clicking on existing hold
    const clickedHoldIndex = currentHolds.findIndex(([hx, hy]) => {
        const dist = Math.sqrt((x - hx) ** 2 + (y - hy) ** 2);
        return dist < 20; // 20 pixel radius
    });
    
    if (clickedHoldIndex >= 0) {
        // Single click: remove hold
        if (finishHoldIndex === clickedHoldIndex) {
            finishHoldIndex = null; // Clear finish if removing finish hold
        }
        currentHolds.splice(clickedHoldIndex, 1);
        // Adjust finish index if needed
        if (finishHoldIndex !== null && finishHoldIndex > clickedHoldIndex) {
            finishHoldIndex--;
        }
        drawHoldsOnCanvas();
    } else {
        // Add new hold
        currentHolds.push([x, y]);
        drawHoldsOnCanvas();
    }
}

/**
 * Handle canvas double click to mark/unmark finish hold
 */
function handleCanvasDoubleClick(event) {
    if (roiMode) return; // ROI mode doesn't handle double clicks
    
    const coords = getCanvasCoordinates(event);
    const x = coords.x;
    const y = coords.y;
    
    // Check if double-clicking on existing hold
    const clickedHoldIndex = currentHolds.findIndex(([hx, hy]) => {
        const dist = Math.sqrt((x - hx) ** 2 + (y - hy) ** 2);
        return dist < 20; // 20 pixel radius
    });
    
    if (clickedHoldIndex >= 0) {
        // Toggle finish hold
        if (finishHoldIndex === clickedHoldIndex) {
            // Unmark as finish hold
            finishHoldIndex = null;
        } else {
            // Mark as finish hold
            finishHoldIndex = clickedHoldIndex;
        }
        drawHoldsOnCanvas();
    }
}

/**
 * Update canvas mode display
 */
function updateCanvasMode() {
    const modeText = document.getElementById('canvasMode');
    const useRoiCheckbox = document.getElementById('useRoiCheckbox');
    
    if (roiMode && useRoiCheckbox && useRoiCheckbox.checked) {
        modeText.textContent = 'Arrastra para seleccionar la región del escalador (ROI)';
        if (canvas) {
            canvas.style.cursor = 'crosshair';
        }
    } else {
        modeText.textContent = 'Haz clic para añadir presas manualmente';
        if (canvas) {
            canvas.style.cursor = 'default';
        }
    }
}

/**
 * Update ROI info display
 */
function updateRoiInfo() {
    const roiInfo = document.getElementById('roiInfo');
    const roiDimensions = document.getElementById('roiDimensions');
    
    if (currentRoi) {
        if (roiInfo) roiInfo.classList.remove('hidden');
        if (roiDimensions) {
            roiDimensions.textContent = `${currentRoi.width}x${currentRoi.height} píxeles en (${currentRoi.x}, ${currentRoi.y})`;
        }
    } else {
        if (roiInfo) roiInfo.classList.add('hidden');
    }
}

/**
 * Confirm holds and start analysis
 */
async function confirmAndAnalyze(videoId, climberWeight, originalFile) {
    const modal = document.getElementById('holdDetectionModal');
    const uploadStatus = document.getElementById('uploadStatus');
    const useRoiCheckbox = document.getElementById('useRoiCheckbox');
    
    if (currentHolds.length === 0) {
        alert('Por favor añade al menos una presa antes de analizar');
        return;
    }
    
    try {
        modal.classList.add('hidden');
        showLoading(true);
        showStatus(uploadStatus, 'Analizando video...', 'info');
        
        // Prepare request data
        const requestData = {
            climber_weight: climberWeight,
            custom_holds: currentHolds,
            finish_hold_index: finishHoldIndex  // Include finish hold index
        };
        
        // Add ROI if checkbox is checked and ROI exists
        if (useRoiCheckbox.checked && currentRoi) {
            requestData.roi = [currentRoi.x, currentRoi.y, currentRoi.width, currentRoi.height];
            console.log('Enviando ROI al backend:', requestData.roi);
        }
        
        // Log what we're sending
        console.log('Enviando datos al backend:', {
            climber_weight: requestData.climber_weight,
            custom_holds_count: requestData.custom_holds.length,
            finish_hold_index: requestData.finish_hold_index,
            has_roi: !!requestData.roi
        });
        
        // Analyze with custom holds and optional ROI
        const analyzeResponse = await fetch(`${API_BASE_URL}/analyze/${videoId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!analyzeResponse.ok) {
            throw new Error('Error al analizar el video');
        }
        
        const analysisData = await analyzeResponse.json();
        
        showStatus(uploadStatus, 'Análisis completado. Cargando video procesado...', 'info');
        
        // Load overlay video
        const overlayUrl = `${API_BASE_URL}/overlay/${videoId}`;
        
        // Display results
        await displayResults(analysisData, originalFile, overlayUrl);
        
        showStatus(uploadStatus, 'Análisis completado', 'success');
    } catch (error) {
        console.error('Error:', error);
        showStatus(uploadStatus, `Error: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}
