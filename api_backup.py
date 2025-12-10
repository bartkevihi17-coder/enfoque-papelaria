(function() {
  // --------- Configuração da API ---------
  // SUA API NO RENDER:
  const API_BASE = "https://enfoque-papelaria.onrender.com";

  function getMobileBackupUrl() {
    return API_BASE.replace(/\/+$/, "") + "/api/backup/from-mobile/enfoque";
  }

  // --------- Estado ---------
  const STORAGE_KEY = "leitorEstoqueData_v4";

  let state = {
    folders: [],
    currentFolderId: null,
    screen: "folders"
  };

  let scanning = false;
  let codeReader = null;
  let lastScanTime = 0;
  let activeCode = null;

  // --------- Utils ---------
  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed.folders)) {
        state.folders = parsed.folders;
      }
    } catch (e) {
      console.warn("Erro lendo localStorage", e);
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ folders: state.folders }));
    } catch (e) {
      console.warn("Erro salvando localStorage", e);
    }
  }

  function createFolder(name) {
    const trimmed = (name || "").trim();
    if (!trimmed) return null;
    const folder = {
      id: "fld_" + Date.now() + "_" + Math.random().toString(16).slice(2),
      name: trimmed,
      createdAt: new Date().toISOString(),
      items: []
    };
    state.folders.push(folder);
    saveState();
    return folder;
  }

  function getFolder(id) {
    return state.folders.find((f) => f.id === id) || null;
  }

  function setCurrentFolder(id) {
    state.currentFolderId = id;
  }

  function upsertItemInCurrentFolder(code, updateQuantityFn) {
    const folder = getFolder(state.currentFolderId);
    if (!folder) return;

    const trimmed = String(code || "").trim();
    if (!trimmed) return;

    let item = folder.items.find((i) => i.code === trimmed);
    if (!item) {
      item = { code: trimmed, quantity: 0 };
      folder.items.push(item);
    }

    const newQty = updateQuantityFn(item.quantity);
    item.quantity = Math.max(1, newQty || 1);

    saveState();
    renderFolderItems();
    renderScannerItems();
  }

  function formatDateShort(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
    } catch {
      return "";
    }
  }

  function showToast(msg) {
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.classList.remove("hidden");
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => {
      toast.classList.add("hidden");
    }, 2200);
  }

  // --------- Navegação ---------
  function setScreen(screen) {
    state.screen = screen;
    const screens = ["folders", "folderDetail", "scanner"];

    screens.forEach((name) => {
      const mainEl = document.getElementById(name + "Screen");
      const headerEl = document.querySelector('.top-bar[data-screen="' + name + '"]');

      if (name === screen) {
        mainEl && mainEl.classList.add("active");
        mainEl && mainEl.classList.remove("hidden");
        headerEl && headerEl.classList.remove("hidden");
      } else {
        mainEl && mainEl.classList.remove("active");
        mainEl && mainEl.classList.add("hidden");
        headerEl && headerEl.classList.add("hidden");
      }
    });

    if (screen !== "scanner") {
      stopScanner();
    } else {
      startScanner();
    }
  }

  // --------- Render pastas ---------
  function renderFolders() {
    const listEl = document.getElementById("foldersList");
    const emptyEl = document.getElementById("foldersEmpty");

    listEl.innerHTML = "";

    if (!state.folders.length) {
      emptyEl.classList.remove("hidden");
      listEl.classList.add("hidden");
      return;
    }

    emptyEl.classList.add("hidden");
    listEl.classList.remove("hidden");

    state.folders
      .slice()
      .reverse()
      .forEach((folder) => {
        const li = document.createElement("li");

        const left = document.createElement("div");
        left.className = "folder-title";
        const nameSpan = document.createElement("span");
        nameSpan.className = "name";
        nameSpan.textContent = folder.name;
        const metaSpan = document.createElement("span");
        metaSpan.className = "meta";
        metaSpan.textContent =
          (folder.items?.length || 0) + " itens • " + formatDateShort(folder.createdAt);
        left.appendChild(nameSpan);
        left.appendChild(metaSpan);

        const arrow = document.createElement("span");
        arrow.textContent = "›";
        arrow.style.opacity = "0.6";

        li.appendChild(left);
        li.appendChild(arrow);

        li.addEventListener("click", () => {
          setCurrentFolder(folder.id);
          renderFolderDetail();
          setScreen("folderDetail");
        });

        listEl.appendChild(li);
      });
  }

  // --------- Render itens ---------
  function renderFolderItems() {
    const folder = getFolder(state.currentFolderId);
    const listEl = document.getElementById("itemsList");
    const emptyEl = document.getElementById("folderItemsEmpty");

    if (!folder) {
      listEl.innerHTML = "";
      emptyEl.classList.remove("hidden");
      return;
    }

    listEl.innerHTML = "";

    if (!folder.items.length) {
      emptyEl.classList.remove("hidden");
      return;
    }

    emptyEl.classList.add("hidden");

    folder.items.forEach((item) => {
      const li = document.createElement("li");

      const left = document.createElement("div");
      left.className = "item-left";
      const codeSpan = document.createElement("span");
      codeSpan.className = "item-code";
      codeSpan.textContent = item.code;
      const labelSpan = document.createElement("span");
      labelSpan.className = "item-label";
      labelSpan.textContent = "Quantidade";
      left.appendChild(codeSpan);
      left.appendChild(labelSpan);

      const right = document.createElement("div");
      right.className = "item-right";

      const input = document.createElement("input");
      input.type = "number";
      input.min = "1";
      input.className = "item-qty-input";
      input.value = item.quantity;
      input.addEventListener("change", () => {
        const v = parseInt(input.value, 10);
        item.quantity = isNaN(v) || v <= 0 ? 1 : v;
        saveState();
        renderScannerItems();
      });

      right.appendChild(input);
      li.appendChild(left);
      li.appendChild(right);

      listEl.appendChild(li);
    });
  }

  function renderFolderDetail() {
    const folder = getFolder(state.currentFolderId);
    const titleEl = document.getElementById("folderTitle");
    if (folder) {
      titleEl.textContent = folder.name;
    } else {
      titleEl.textContent = "Pasta";
    }
    renderFolderItems();
  }

  function renderScannerItems() {
    const folder = getFolder(state.currentFolderId);
    const listEl = document.getElementById("scannerItemsList");
    if (!folder) {
      listEl.innerHTML = "";
      return;
    }
    listEl.innerHTML = "";
    folder.items
      .slice()
      .reverse()
      .forEach((item) => {
        const li = document.createElement("li");

        const left = document.createElement("div");
        left.className = "item-left";
        const code = document.createElement("span");
        code.className = "item-code";
        code.textContent = item.code;
        const qty = document.createElement("span");
        qty.className = "item-label";
        qty.textContent = "Qtd: " + item.quantity;
        left.appendChild(code);
        left.appendChild(qty);

        li.appendChild(left);
        listEl.appendChild(li);
      });
  }

  // --------- Scanner com ZXing ---------
  async function startScanner() {
    if (scanning) return;
    const statusEl = document.getElementById("scannerStatus");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      statusEl.textContent = "Este navegador não permite acesso à câmera.";
      return;
    }

    if (!window.ZXing || !ZXing.BrowserMultiFormatReader) {
      statusEl.textContent = "Biblioteca de leitura não carregou. Verifique sua conexão.";
      return;
    }

    const folder = getFolder(state.currentFolderId);
    if (!folder) {
      statusEl.textContent = "Selecione uma pasta antes de ler.";
      return;
    }

    let hints = null;
    try {
      if (ZXing.DecodeHintType && ZXing.BarcodeFormat) {
        hints = new Map();
        const formats = [
          ZXing.BarcodeFormat.EAN_13,
          ZXing.BarcodeFormat.EAN_8,
          ZXing.BarcodeFormat.UPC_A,
          ZXing.BarcodeFormat.UPC_E,
          ZXing.BarcodeFormat.CODE_128,
          ZXing.BarcodeFormat.CODE_39
        ];
        hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, formats);
      }
    } catch (e) {
      console.warn("Não foi possível configurar hints do ZXing, usando padrão.", e);
    }

    try {
      codeReader = hints
        ? new ZXing.BrowserMultiFormatReader(hints, 250)
        : new ZXing.BrowserMultiFormatReader(undefined, 250);
    } catch (e) {
      console.error("Erro criando BrowserMultiFormatReader", e);
      statusEl.textContent = "Erro iniciando leitor de código.";
      return;
    }

    scanning = true;
    lastScanTime = 0;
    activeCode = null;
    renderScannerItems();

    try {
      const devices = await codeReader.listVideoInputDevices();
      let deviceId;

      if (devices && devices.length) {
        const back = devices.find((d) => /back|trás|rear|environment/i.test(d.label));
        deviceId = (back || devices[0]).deviceId;
      }

      await codeReader.decodeFromConstraints(
        {
          video: {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            facingMode: { ideal: "environment" },
            width: { ideal: 1280, min: 640 },
            height: { ideal: 720, min: 480 }
          }
        },
        "videoPreview",
        (result, err) => {
          if (!scanning) return;
          if (result) {
            const text = result.getText();
            const now = Date.now();
            if (!text) return;
            if (now - lastScanTime > 400 || text !== activeCode) {
              lastScanTime = now;
              handleNewScan(text);
            }
          }
        }
      );
    } catch (err) {
      console.error("Erro ao iniciar câmera/leitor", err);
      statusEl.textContent = "Erro ao iniciar a câmera ou leitor.";
      scanning = false;
    }
  }

  function stopScanner() {
    scanning = false;
    if (codeReader) {
      try {
        codeReader.reset();
      } catch (e) {
        console.warn("Erro ao resetar codeReader", e);
      }
      codeReader = null;
    }
    const video = document.getElementById("videoPreview");
    if (video) {
      video.srcObject = null;
    }
  }

  function handleNewScan(code) {
    const trimmed = String(code || "").trim();
    if (!trimmed) return;

    const quantityInput = document.getElementById("quantityInput");

    if (activeCode && quantityInput.value) {
      const q = parseInt(quantityInput.value, 10);
      if (!isNaN(q) && q > 0) {
        upsertItemInCurrentFolder(activeCode, () => q);
      }
      quantityInput.value = "";
    }

    upsertItemInCurrentFolder(trimmed, (current) => current + 1);

    activeCode = trimmed;
    const popupCodeLabel = document.getElementById("popupCodeLabel");
    popupCodeLabel.textContent = "Código lido: " + trimmed;
    quantityInput.value = "";
    showQuantityPopup(true);
  }

  function showQuantityPopup(show) {
    const popup = document.getElementById("quantityPopup");
    if (show) {
      popup.classList.remove("hidden");
      setTimeout(() => {
        document.getElementById("quantityInput").focus();
      }, 100);
    } else {
      popup.classList.add("hidden");
    }
  }

  function applyQuantityAndClose(useInput) {
    const quantityInput = document.getElementById("quantityInput");
    if (useInput && activeCode && quantityInput.value) {
      const q = parseInt(quantityInput.value, 10);
      if (!isNaN(q) && q > 0) {
        upsertItemInCurrentFolder(activeCode, () => q);
      }
    }
    quantityInput.value = "";
    showQuantityPopup(false);
  }

  // --------- Exportações ---------
  function exportCurrentFolderCSV() {
    const folder = getFolder(state.currentFolderId);
    if (!folder) return;
    if (!folder.items.length) {
      showToast("Nenhum item para exportar.");
      return;
    }

    let csv = "codigo,quantidade\n";
    folder.items.forEach((item) => {
      csv += `${item.code},${item.quantity}\n`;
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safeName = folder.name.replace(/[^a-z0-9_-]+/gi, "_").toLowerCase();
    a.href = url;
    a.download = `inventario_${safeName || "pasta"}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast("CSV exportado.");
  }

  function exportCurrentFolderBackup() {
    const folder = getFolder(state.currentFolderId);
    if (!folder) return;
    if (!folder.items.length) {
      showToast("Nenhum item para exportar.");
      return;
    }

    const origem = window.prompt("Origem (opcional):", "") || "";
    const destino = window.prompt("Destino (opcional):", "") || "";
    const responsavel = window.prompt("Responsável (opcional):", "") || "";

    const now = new Date();
    const dataStr =
      now.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric"
      }) +
      " - " +
      now.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit"
      });

    const backup = {
      origem,
      destino,
      responsavel,
      data: dataStr,
      itens: (getFolder(state.currentFolderId).items || []).map((item) => ({
        codigo: item.code,
        quantidade: item.quantity
      }))
    };

    // 1) Baixar localmente como JSON
    const jsonStr = JSON.stringify(backup, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safeName = folder.name.replace(/[^a-z0-9_-]+/gi, "_").toLowerCase();
    a.href = url;
    a.download = `backup_${safeName || "pasta"}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // 2) Enviar para a API
    const apiUrl = getMobileBackupUrl();

    fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(backup)
    })
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json().catch(() => ({}));
      })
      .then(() => {
        showToast("Backup enviado para a API com sucesso.");
      })
      .catch((err) => {
        console.error("[Leitor Estoque] Erro ao enviar backup para a API:", err);
        showToast("Backup salvo (arquivo). Erro ao enviar para API.");
      });
  }

  // --------- Eventos ---------
  function initEvents() {
    document.getElementById("btnNewFolder").addEventListener("click", () => {
      const name = window.prompt("Nome da pasta:");
      if (!name) return;
      const folder = createFolder(name);
      if (folder) {
        renderFolders();
        setCurrentFolder(folder.id);
        renderFolderDetail();
        setScreen("folderDetail");
      }
    });

    document.getElementById("btnCreateFirstFolder").addEventListener("click", () => {
      const name = window.prompt("Nome da pasta:");
      if (!name) return;
      const folder = createFolder(name);
      if (folder) {
        renderFolders();
        setCurrentFolder(folder.id);
        renderFolderDetail();
        setScreen("folderDetail");
      }
    });

    document.getElementById("btnBackToFolders").addEventListener("click", () => {
      setScreen("folders");
      renderFolders();
    });

    document.getElementById("btnStartScan").addEventListener("click", () => {
      setScreen("scanner");
    });

    document.getElementById("btnBackToFolder").addEventListener("click", () => {
      setScreen("folderDetail");
      renderFolderDetail();
    });

    document.getElementById("btnPopupSkip").addEventListener("click", () => {
      applyQuantityAndClose(false);
    });
    document.getElementById("btnPopupOk").addEventListener("click", () => {
      applyQuantityAndClose(true);
    });

    document.getElementById("btnExportCSV").addEventListener("click", exportCurrentFolderCSV);
    document.getElementById("btnExportBackup").addEventListener("click", exportCurrentFolderBackup);
  }

  function init() {
    loadState();
    renderFolders();
    initEvents();
    setScreen("folders");
  }

  document.addEventListener("DOMContentLoaded", init);
})();
