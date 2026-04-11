/* eslint-disable no-undef */

import * as pdfjsLib from 'pdfjs-dist/build/pdf.min.mjs';
import * as pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs';

import { GlobalWorkerOptions } from 'pdfjs-dist';
const workerBlob = new Blob([pdfWorker], { type: 'application/javascript' });
const workerBlobUrl = URL.createObjectURL(workerBlob);
GlobalWorkerOptions.workerSrc = workerBlobUrl;

const mediaViewer = document.getElementById("media-viewer");
const pdfViewer = document.getElementById("pdf-viewer");
const pdfCanvas = document.getElementById("pdf-canvas");
const pdfControlNext = document.getElementById("next-page-btn");
const pdfControlPrev = document.getElementById("prev-page-btn");
const pdfControlPage = document.getElementById("page-number");
const pdfControlPageCount = document.getElementById("page-count");
let pdfDoc = null;
let pageNum = 1;
let pageCount = 0;


function receiveMessage(event) {
  const url = URL.createObjectURL(event.data.blob);

  if (event.data.tag === "pdf") {
    pdfViewer.style.display = "block";
    mediaViewer.style.display = "none";
    createPdfViewer(url);
  } else {
    pdfViewer.style.display = "none";
    mediaViewer.style.display = "block";
    mediaViewer.replaceChildren();

    let viewerElement;

    switch (event.data.tag) {
      case "audio":
        viewerElement = document.createElement("audio");
        viewerElement.controls = true;
        viewerElement.src = url;
        break;
      case "video":
        viewerElement = document.createElement("video");
        viewerElement.controls = true;
        viewerElement.src = url;
        break;
      case "image":
        viewerElement = document.createElement("img");
        viewerElement.src = url;
        break;
      case "txt":
        event.data.blob.text().then((text) => {
          const pre = document.createElement("pre");
          pre.textContent = text;
          mediaViewer.appendChild(pre);
        });
        return; // Exit early for async text loading
      default:
        console.warn("Unsupported media type:", event.data.tag);
        return;
    }

    // Append the created viewer element
    if (viewerElement) {
      viewerElement.id = "viewer";
      mediaViewer.appendChild(viewerElement);
    }
  }
}


function createPdfViewer(url) {
  pdfjsLib.getDocument(url).promise.then((pdfDoc_) => {
    pdfDoc = pdfDoc_;
    pageCount = pdfDoc.numPages;
    pdfControlPageCount.textContent = pageCount;
    pageNum = 1;
    renderPage(pageNum);
  });

  pdfControlNext.addEventListener("click", pdfNextPage);
  pdfControlPrev.addEventListener("click", pdfPrevPage);
}

function renderPage(num) {
  pdfDoc.getPage(num).then((page) => {
    const scale = pdfCanvas.clientWidth / page.getViewport({ scale: 1 }).width;
    const viewport = page.getViewport({ scale });
    pdfCanvas.width = viewport.width;
    pdfCanvas.height = viewport.height;

    const context = pdfCanvas.getContext("2d");
    page.render({ canvasContext: context, viewport }).promise.then(() => {
      pdfControlPage.textContent = pageNum;
      pdfControlPrev.disabled = pageNum <= 1;
      pdfControlNext.disabled = pageNum >= pageCount;
    });
  });
}

function pdfNextPage() {
  if (pageNum < pageCount) {
    pageNum++;
    renderPage(pageNum);
  }
}

function pdfPrevPage() {
  if (pageNum > 1) {
    pageNum--;
    renderPage(pageNum);
  }
}

window.addEventListener(
  "load",
  function () {
    if (window.self === window.top) {
      return;
    };

    window.parent.postMessage("ready", "*");
    window.addEventListener("message", receiveMessage, {once: true});
  },
  true
);

window.addEventListener(
  "unload",
  function () {
    pdfControlNext.removeEventListener("click", pdfNextPage);
    pdfControlPrev.removeEventListener("click", pdfPrevPage);
  },
  true
);
