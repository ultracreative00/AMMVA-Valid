/* AAMVA Validator — Frontend Logic */
"use strict";

const fileInput  = document.getElementById("fileInput");
const preview    = document.getElementById("preview");
const btn        = document.getElementById("validateBtn");
const spinner    = document.getElementById("spinner");
const resultCard = document.getElementById("result");
const dropZone   = document.getElementById("dropZone");

fileInput.addEventListener("change", () => {
  const f = fileInput.files[0];
  if (!f) return;
  preview.src = URL.createObjectURL(f);
  preview.hidden = false;
  btn.disabled = false;
  resultCard.hidden = true;
});

["dragover", "dragenter"].forEach(ev =>
  dropZone.addEventListener(ev, e => { e.preventDefault(); dropZone.classList.add("drag"); })
);
["dragleave", "drop"].forEach(ev =>
  dropZone.addEventListener(ev, e => {
    e.preventDefault();
    dropZone.classList.remove("drag");
    if (ev === "drop" && e.dataTransfer.files[0]) {
      const dt = new DataTransfer();
      dt.items.add(e.dataTransfer.files[0]);
      fileInput.files = dt.files;
      fileInput.dispatchEvent(new Event("change"));
    }
  })
);

dropZone.addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === " ") fileInput.click();
});

btn.addEventListener("click", async () => {
  const f = fileInput.files[0];
  if (!f) return;
  btn.disabled = true;
  spinner.hidden = false;
  resultCard.hidden = true;
  const fd = new FormData();
  fd.append("file", f);
  try {
    const resp = await fetch("/validate", { method: "POST", body: fd });
    const data = await resp.json();
    spinner.hidden = true;
    renderResult(data);
  } catch (err) {
    spinner.hidden = true;
    alert("Server error: " + err.message);
  } finally {
    btn.disabled = false;
  }
});

function renderResult(d) {
  resultCard.hidden = false;
  const score = typeof d.score === "number" ? d.score : 0;

  const vb = document.getElementById("verdictBox");
  vb.innerHTML = "";
  const verdict = document.createElement("div");
  verdict.className = "verdict " + (d.valid ? "pass" : "fail");
  verdict.innerHTML = d.valid
    ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg> BARCODE VALID &#8212; Passes AAMVA Compliance`
    : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg> BARCODE FAILED AAMVA VALIDATION`;
  vb.appendChild(verdict);

  document.getElementById("scoreLabel").textContent = `Authenticity Score: ${score} / 100`;
  const fill = document.getElementById("scoreFill");
  fill.style.width  = score + "%";
  fill.style.background = score >= 80 ? "#238636" : score >= 50 ? "#d29922" : "#da3633";
  document.getElementById("scoreBar").setAttribute("aria-valuenow", score);

  const ib = document.getElementById("issuerBlock");
  if (d.fields && d.fields.issuer) {
    const j = d.fields.issuer;
    const agree = d.engine_agreement !== false;
    ib.innerHTML =
      `<p class="section-title">Issuing Jurisdiction</p>
       <div class="tag-list">
         <span class="tag ok">IIN: ${esc(j.iin)}</span>
         <span class="tag ok">${esc(j.state)} (${esc(j.abbreviation)})</span>
         <span class="tag ok">${j.country === "US" ? "United States" : "Canada"}</span>
         ${d.fields.aamva_version ? `<span class="tag ok">AAMVA v${d.fields.aamva_version}</span>` : ""}
         ${d.subfile_type ? `<span class="tag ok">Subfile: ${esc(d.subfile_type)}</span>` : ""}
         ${d.decode_engines ? `<span class="tag ok">Engine(s): ${esc(d.decode_engines.join(", "))}</span>` : ""}
         <span class="tag ${agree ? "ok" : "err'}">${agree ? "Engines Agree &#10003;" : "Engine Disagreement &#9888;"}</span>
       </div>`;
  } else {
    ib.innerHTML = "";
  }

  const issB = document.getElementById("issuesBlock");
  if (d.issues && d.issues.length) {
    issB.innerHTML =
      `<p class="section-title">&#10060; Compliance Issues (${d.issues.length})</p>
       <div class="tag-list">${d.issues.map(i => `<span class="tag err">${esc(i)}</span>`).join("")}</div>`;
  } else {
    issB.innerHTML = `<p class="section-title" style="color:#56d364">&#10003; No compliance issues found</p>`;
  }

  const wB = document.getElementById("warningsBlock");
  if (d.warnings && d.warnings.length) {
    wB.innerHTML =
      `<p class="section-title">&#9888; Warnings (${d.warnings.length})</p>
       <div class="tag-list">${d.warnings.map(w => `<span class="tag warn">${esc(w)}</span>`).join("")}</div>`;
  } else {
    wB.innerHTML = "";
  }

  const fB   = document.getElementById("fieldsBlock");
  const skip = new Set(["elements","issuer","aamva_version"]);
  const pf   = Object.entries(d.fields || {}).filter(([k,v]) => !skip.has(k) && typeof v === "string");
  if (pf.length) {
    fB.innerHTML =
      `<p class="section-title" style="margin-top:.75rem">Parsed Identity Fields</p>
       <table>
         <thead><tr><th>Field</th><th>Value</th></tr></thead>
         <tbody>${pf.map(([k,v]) => `<tr><td>${esc(k.replace(/_/g," "))}</td><td>${esc(v)}</td></tr>`).join("")}</tbody>
       </table>`;
  } else {
    fB.innerHTML = "";
  }

  const eB  = document.getElementById("elementsBlock");
  const els = d.fields && d.fields.elements;
  if (els && Object.keys(els).length) {
    eB.innerHTML =
      `<details>
         <summary>&#9658; Raw AAMVA Data Elements (${Object.keys(els).length})</summary>
         <table style="margin-top:.5rem">
           <thead><tr><th>Element ID</th><th>Value</th></tr></thead>
           <tbody>${Object.entries(els).map(([k,v]) => `<tr><td><code>${esc(k)}</code></td><td>${esc(v)}</td></tr>`).join("")}</tbody>
         </table>
       </details>`;
  } else {
    eB.innerHTML = "";
  }

  resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
