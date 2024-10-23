/* eslint-disable no-undef */

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

function receiveMessage(evt) {
  const url = URL.createObjectURL(evt.data.blob);
  if (evt.data.tag === "pdf") {
    pdfViewer.style.display = "block";
    mediaViewer.style.display = "none";
    createPdfViewer(url);
  } else {
    pdfViewer.style.display = "none";
    mediaViewer.style.display = "block";
    if (evt.data.tag === "audio") {
      mediaViewer.innerHTML =
        "<audio id=\"viewer\" src=\"" + url + "\" controls /></audio>";
    } else if (evt.data.tag === "image") {
      mediaViewer.innerHTML =
        "<img id=\"viewer\" src=\"" + url + "\" />";
    } else if (evt.data.tag === "video") {
      mediaViewer.innerHTML =
        "<video id=\"viewer\" src=\"" + url + "\" controls /></video>";
    } else if (evt.data.tag === "txt") {
      evt.data.blob.text().then(function (text) {
        mediaViewer.innerHTML =
          "<pre id=\"viewer\">" + text + "</pre>";
      });
    }
  }
}

function createPdfViewer(url) {
  pdfjsLib.getDocument(url).promise.then(function (pdfDoc_) {
    pdfDoc = pdfDoc_;
    pageCount = pdfDoc.numPages;
    pdfControlPageCount.innerHTML = pageCount;
    pdfControlPage.innerText = 0;
    renderPage(pageNum);
  });

  pdfControlNext.addEventListener("click", pdfNextPage);
  pdfControlPrev.addEventListener("click", pdfPrevPage);
}

function renderPage(num) {
  pdfDoc.getPage(num).then(function (page) {
    // find scale to fit page in canvas
    const scale = pdfCanvas.clientWidth / page.getViewport({scale: 1.0}).width;
    const viewport = page.getViewport({scale: scale});
    const canvas = pdfCanvas;
    const context = canvas.getContext("2d");
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const renderContext = {
      canvasContext: context,
      viewport: viewport,
    };
    const renderTask = page.render(renderContext);
    renderTask.promise.then(function () {
      // updating label
      pdfControlPage.innerText = pageNum;
      // disable and enable control buttons
      if (pageNum <= 1) {
        pdfControlPrev.disabled = true;
      }
      if (pageNum >= pageCount) {
        pdfControlNext.disabled = true;
      }
      if (pageNum > 1) {
        pdfControlPrev.disabled = false;
      }
      if (pageNum < pageCount) {
        pdfControlNext.disabled = false;
      }
    });
  });
}

function pdfNextPage() {
  if (pageNum >= pageCount) {
    return;
  }
  pageNum++;
  pdfControlPage.value = pageNum;
  renderPage(pageNum);
}

function pdfPrevPage() {
  if (pageNum <= 1) {
    return;
  }
  pageNum--;
  pdfControlPage.value = pageNum;
  renderPage(pageNum);
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
