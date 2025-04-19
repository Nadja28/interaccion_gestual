let currentPage = 1;
let maxPages = 1;
let gestureTimer = null;
let zoomLevel = 1.0;

const pdfImage = document.getElementById('pdf-image');
const pageCounter = document.getElementById('page-counter');
const gestureInfo = document.getElementById('gesture-info');

const socket = new WebSocket("ws://127.0.0.1:8000/ws/gestures");

let pendingGesture = null;
let approved = false;

fetch("/get_total_pages")
  .then(res => res.json())
  .then(data => {
    maxPages = data.total_pages;
    updatePageCounter();
  });

function updatePageCounter() {
    pageCounter.innerText = `P. ${currentPage}/${maxPages}`;
}

function updateGestureInfo(message) {
    gestureInfo.innerText = message;
}

function applyZoom() {
    pdfImage.style.transform = `scale(${zoomLevel})`;
}

socket.onmessage = function(event) {
    const gesture = event.data;
    console.log("Gesto detectado:", gesture);
    updateGestureInfo(gesture);

    if (gesture === "pulgar arriba" && pendingGesture) {
        approved = true;
    } else if (["dedo derecha", "dedo izquierda", "puño", "palma"].includes(gesture)) {
        pendingGesture = gesture;
        approved = false;
    }

    if (approved && pendingGesture) {
        if (gestureTimer) clearTimeout(gestureTimer);

        gestureTimer = setTimeout(() => {
            if (pendingGesture === "dedo derecha" && currentPage < maxPages) {
                currentPage++;
            } else if (pendingGesture === "dedo izquierda" && currentPage > 1) {
                currentPage--;
            } else if (pendingGesture === "palma") {
                zoomLevel = Math.min(zoomLevel + 0.2, 2);
                applyZoom();
            } else if (pendingGesture === "puño") {
                zoomLevel = Math.max(zoomLevel - 0.2, 1);
                applyZoom();
            }

            if (["dedo derecha", "dedo izquierda"].includes(pendingGesture)) {
                const url = `/get_pdf_page/${currentPage}`;
                pdfImage.src = url;
                updatePageCounter();
                console.log("Página cargada:", url);
            }

            pendingGesture = null;
            approved = false;
        }, 500);
    }
};

updatePageCounter();
updateGestureInfo("Esperando gesto...");
