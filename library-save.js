// ═══════════════════════════════════════════════════════
// LIBRARY SAVE HELPER – shared across all pages
// ═══════════════════════════════════════════════════════
(function () {
    const LIB_KEY = 'liftoffLibrary';

    function _getLib() {
        let lib = JSON.parse(localStorage.getItem(LIB_KEY));
        if (!lib) {
            lib = {
                folders: [
                    { id: 'notes', name: '📝 Notes', items: [] },
                    { id: 'flowcharts', name: '📊 Flowcharts', items: [] }
                ]
            };
            localStorage.setItem(LIB_KEY, JSON.stringify(lib));
        }
        return lib;
    }

    function _saveLib(lib) {
        localStorage.setItem(LIB_KEY, JSON.stringify(lib));
    }

    function _genId() {
        return 'lib_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    }

    function _escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    /**
     * Save an item to a library folder.
     * @param {string} type       'note' | 'flowchart'
     * @param {string} content    The rendered HTML (notes) or mermaid code (flowcharts)
     * @param {string} pdfName    Source PDF name (optional)
     * @param {string} [defaultName] Suggested name
     * @param {string} [targetFolder] Folder id to save into (defaults to 'notes' or 'flowcharts')
     * @returns {boolean} true if saved
     */
    function saveToLibrary(type, content, pdfName, defaultName, targetFolder) {
        const lib = _getLib();
        const folderId = targetFolder || (type === 'flowchart' ? 'flowcharts' : 'notes');

        // Prompt user for name
        const name = prompt('Name this item:', defaultName || (pdfName ? pdfName.replace('.pdf', '') : (type === 'flowchart' ? 'Flowchart' : 'Notes')));
        if (!name) return false;

        // Find or create target folder
        let folder = lib.folders.find(f => f.id === folderId);
        if (!folder) {
            folder = { id: folderId, name: folderId, items: [] };
            lib.folders.push(folder);
        }

        folder.items.unshift({
            id: _genId(),
            name: name.trim(),
            type: type,
            content: content,
            pdfName: pdfName || '',
            createdAt: new Date().toISOString()
        });

        _saveLib(lib);
        return true;
    }

    /**
     * Auto-save (no prompt) — used for automatic saves after generation.
     */
    function autoSaveToLibrary(type, content, pdfName, itemName) {
        const lib = _getLib();
        const folderId = type === 'flowchart' ? 'flowcharts' : 'notes';

        let folder = lib.folders.find(f => f.id === folderId);
        if (!folder) {
            folder = { id: folderId, name: folderId === 'notes' ? '📝 Notes' : '📊 Flowcharts', items: [] };
            lib.folders.push(folder);
        }

        const finalName = itemName || (pdfName ? pdfName.replace('.pdf', '') : (type === 'flowchart' ? 'Flowchart' : 'Notes'));

        folder.items.unshift({
            id: _genId(),
            name: finalName,
            type: type,
            content: content,
            pdfName: pdfName || '',
            createdAt: new Date().toISOString()
        });

        _saveLib(lib);
        return true;
    }

    /**
     * Get all folders (for folder picker UI).
     */
    function getLibraryFolders() {
        return _getLib().folders;
    }

    /**
     * Get all items of a given type across all folders.
     */
    function getAllItems(type) {
        const lib = _getLib();
        const results = [];
        lib.folders.forEach(f => {
            f.items.forEach(item => {
                if (!type || item.type === type) {
                    results.push({ ...item, folderName: f.name, folderId: f.id });
                }
            });
        });
        return results;
    }

    /**
     * Show a save-to-library modal with name input + folder picker.
     */
    function showSaveModal(type, content, pdfName, defaultName, callback) {
        const lib = _getLib();
        const defaultFolder = type === 'flowchart' ? 'flowcharts' : 'notes';

        // Build modal HTML
        const overlay = document.createElement('div');
        overlay.id = 'libSaveOverlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);z-index:100000;display:flex;align-items:center;justify-content:center;';

        let folderOptions = '';
        lib.folders.forEach(f => {
            const sel = f.id === defaultFolder ? ' selected' : '';
            folderOptions += `<option value="${f.id}"${sel}>${_escHtml(f.name)}</option>`;
        });

        overlay.innerHTML = `
            <div style="background:#0f172a;border:1px solid rgba(71,85,105,0.4);border-radius:14px;padding:28px;width:400px;max-width:90vw;">
                <h3 style="margin-bottom:16px;font-size:16px;color:#f1f5f9;">💾 Save to Library</h3>
                <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Name</label>
                <input id="libSaveName" type="text" value="${_escHtml(defaultName || (pdfName ? pdfName.replace('.pdf', '') : ''))}" 
                    style="width:100%;padding:12px 16px;border-radius:8px;border:1px solid rgba(71,85,105,0.4);background:rgba(30,41,59,0.8);color:#f1f5f9;font-size:14px;outline:none;margin-bottom:14px;">
                <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Folder</label>
                <select id="libSaveFolder" style="width:100%;padding:12px 16px;border-radius:8px;border:1px solid rgba(71,85,105,0.4);background:rgba(30,41,59,0.8);color:#f1f5f9;font-size:14px;outline:none;margin-bottom:18px;">
                    ${folderOptions}
                </select>
                <div style="display:flex;gap:10px;justify-content:flex-end;">
                    <button id="libSaveCancel" style="padding:10px 20px;border-radius:8px;border:none;font-weight:600;font-size:13px;cursor:pointer;background:rgba(71,85,105,0.3);color:#94a3b8;">Cancel</button>
                    <button id="libSaveConfirm" style="padding:10px 20px;border-radius:8px;border:none;font-weight:600;font-size:13px;cursor:pointer;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;">Save</button>
                </div>
            </div>`;

        document.body.appendChild(overlay);

        const nameInput = document.getElementById('libSaveName');
        nameInput.focus();
        nameInput.select();

        // Enter key to save
        nameInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') document.getElementById('libSaveConfirm').click();
        });

        document.getElementById('libSaveCancel').onclick = function () {
            overlay.remove();
        };

        document.getElementById('libSaveConfirm').onclick = function () {
            const name = nameInput.value.trim();
            const folderId = document.getElementById('libSaveFolder').value;
            if (!name) { nameInput.style.borderColor = '#ef4444'; return; }

            let folder = lib.folders.find(f => f.id === folderId);
            if (!folder) {
                folder = { id: folderId, name: folderId, items: [] };
                lib.folders.push(folder);
            }

            const item = {
                id: _genId(),
                name: name,
                type: type,
                content: content,
                pdfName: pdfName || '',
                createdAt: new Date().toISOString()
            };

            folder.items.unshift(item);
            _saveLib(lib);
            overlay.remove();

            if (callback) callback(item);
        };

        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) overlay.remove();
        });
    }

    // Expose globally
    window.librarySave = saveToLibrary;
    window.libraryAutoSave = autoSaveToLibrary;
    window.libraryGetFolders = getLibraryFolders;
    window.libraryGetAllItems = getAllItems;
    window.libraryShowSaveModal = showSaveModal;
})();
