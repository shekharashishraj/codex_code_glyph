(function () {
  document.addEventListener("DOMContentLoaded", function () {
    // State management
    const state = {
      selectedWords: new Map(), // word -> {count, replacement}
      highlightMode: false,
      textWords: []
    };

    // DOM elements
    const interactiveText = document.getElementById("interactive-text");
    const selectedMappings = document.getElementById("selected-mappings");
    const manualMappingRows = document.getElementById("manual-mapping-rows");
    const generateBtn = document.getElementById("generate-btn");
    const mappingCount = document.getElementById("mapping-count");
    const highlightToggle = document.getElementById("highlight-toggle");
    const clearSelections = document.getElementById("clear-selections");
    const suggestionContainer = document.querySelector('[data-role="word-suggestions"]');

    if (!interactiveText) return;

    // Initialize interactive text
    function initializeInteractiveText() {
      const text = interactiveText.textContent;
      
      // Split text into words while preserving whitespace and punctuation
      const wordRegex = /(\S+)/g;
      let match;
      const words = [];
      let lastIndex = 0;

      while ((match = wordRegex.exec(text)) !== null) {
        // Add whitespace before word if any
        if (match.index > lastIndex) {
          words.push({
            type: 'whitespace',
            content: text.slice(lastIndex, match.index)
          });
        }
        
        // Add the word
        words.push({
          type: 'word',
          content: match[1],
          index: words.length
        });
        
        lastIndex = match.index + match[1].length;
      }

      // Add remaining whitespace
      if (lastIndex < text.length) {
        words.push({
          type: 'whitespace',
          content: text.slice(lastIndex)
        });
      }

      state.textWords = words;
      renderInteractiveText();
    }

    // Render interactive text with clickable words
    function renderInteractiveText() {
      const html = state.textWords.map(item => {
        if (item.type === 'whitespace') {
          return item.content;
        }
        
        const word = item.content;
        const isSelected = state.selectedWords.has(word.toLowerCase());
        const classes = ['word-selectable'];
        
        if (isSelected) {
          const mapping = state.selectedWords.get(word.toLowerCase());
          classes.push(mapping.replacement ? 'word-mapped' : 'word-selected');
        }
        
        return `<span class="${classes.join(' ')}" data-word="${word}" data-index="${item.index}">${word}</span>`;
      }).join('');

      interactiveText.innerHTML = html;
    }

    // Handle word clicks
    function handleWordClick(event) {
      if (!event.target.classList.contains('word-selectable')) return;
      
      const word = event.target.dataset.word;
      const wordKey = word.toLowerCase();
      
      if (state.selectedWords.has(wordKey)) {
        // Deselect word
        state.selectedWords.delete(wordKey);
        updateWordHighlights(word, false);
      } else {
        // Select word
        const count = countWordOccurrences(word);
        state.selectedWords.set(wordKey, { count, replacement: '', originalWord: word });
        updateWordHighlights(word, true);
      }
      
      renderSelectedMappings();
      updateUI();
    }

    // Count occurrences of a word in text
    function countWordOccurrences(word) {
      return state.textWords.filter(item => 
        item.type === 'word' && item.content.toLowerCase() === word.toLowerCase()
      ).length;
    }

    // Update highlighting for all instances of a word
    function updateWordHighlights(word, selected) {
      const spans = interactiveText.querySelectorAll(`[data-word="${word}"]`);
      spans.forEach(span => {
        if (selected) {
          span.classList.add('word-selected');
        } else {
          span.classList.remove('word-selected', 'word-mapped');
        }
      });
    }

    // Show instance browser for a specific word
    function showInstanceBrowser(word) {
      state.currentWord = word;
      currentWordSpan.textContent = word;
      
      const instances = wordIndexData[word] || [];
      
      let html = '';
      if (instances.length === 0) {
        html = '<p class="text-muted">No instances found</p>';
      } else {
        html = '<div class="row g-2">';
        instances.forEach((instance, index) => {
          const instanceId = `${word}_${instance.page}_${index}`;
          const isSelected = state.selectedInstances.has(instanceId);
          const selectedData = state.selectedInstances.get(instanceId);
          
          html += `
            <div class="col-12">
              <div class="card ${isSelected ? 'border-primary' : ''}">
                <div class="card-body p-3">
                  <div class="form-check">
                    <input class="form-check-input instance-checkbox" type="checkbox" 
                           ${isSelected ? 'checked' : ''} 
                           data-instance-id="${instanceId}"
                           data-word="${word}"
                           data-page="${instance.page}"
                           data-rect="${instance.rect.join(',')}"
                           id="instance-${instanceId}">
                    <label class="form-check-label d-flex justify-content-between align-items-center" for="instance-${instanceId}">
                      <div>
                        <strong>Page ${instance.page + 1}</strong> 
                        <span class="text-muted">• Position: (${Math.round(instance.rect[0])}, ${Math.round(instance.rect[1])})</span>
                      </div>
                      <span class="badge bg-secondary">${word}</span>
                    </label>
                  </div>
                  
                  <div class="mt-2 ${isSelected ? '' : 'd-none'}" id="replacement-${instanceId}">
                    <div class="input-group input-group-sm">
                      <span class="input-group-text">Replace with:</span>
                      <input type="text" class="form-control replacement-input" 
                             value="${selectedData ? selectedData.replacement : ''}"
                             data-instance-id="${instanceId}"
                             placeholder="Enter replacement">
                    </div>
                  </div>
                </div>
              </div>
            </div>
          `;
        });
        html += '</div>';
      }
      
      instanceList.innerHTML = html;
      instanceBrowser.style.display = 'block';
      
      // Scroll to browser
      instanceBrowser.scrollIntoView({ behavior: 'smooth' });
    }

    // Hide instance browser
    function hideInstanceBrowser() {
      instanceBrowser.style.display = 'none';
      state.currentWord = null;
    }

    // Handle instance checkbox changes
    function handleInstanceToggle(checkbox) {
      const instanceId = checkbox.dataset.instanceId;
      const word = checkbox.dataset.word;
      const page = parseInt(checkbox.dataset.page);
      const rect = checkbox.dataset.rect.split(',').map(Number);
      
      if (checkbox.checked) {
        // Add instance to selections
        state.selectedInstances.set(instanceId, {
          word: word,
          page: page,
          rect: rect,
          replacement: ''
        });
        
        // Show replacement input
        const replacementDiv = document.getElementById(`replacement-${instanceId}`);
        if (replacementDiv) {
          replacementDiv.classList.remove('d-none');
          const input = replacementDiv.querySelector('.replacement-input');
          if (input) input.focus();
        }
        
        // Update card styling
        checkbox.closest('.card').classList.add('border-primary');
        
      } else {
        // Remove instance from selections
        state.selectedInstances.delete(instanceId);
        
        // Hide replacement input
        const replacementDiv = document.getElementById(`replacement-${instanceId}`);
        if (replacementDiv) {
          replacementDiv.classList.add('d-none');
        }
        
        // Update card styling
        checkbox.closest('.card').classList.remove('border-primary');
      }
      
      updateSelectedMappings();
      updateUI();
    }

    // Handle replacement input changes
    function handleReplacementChange(input) {
      const instanceId = input.dataset.instanceId;
      const replacement = input.value;
      
      if (state.selectedInstances.has(instanceId)) {
        state.selectedInstances.get(instanceId).replacement = replacement;
        updateSelectedMappings();
        updateUI();
      }
    }

    // Render interactive text with clickable words
    function renderInteractiveText() {
      const html = state.textWords.map(item => {
        if (item.type === 'whitespace') {
          return item.content;
        }
        
        const word = item.content;
        const isSelected = state.selectedWords.has(word.toLowerCase());
        const classes = ['word-selectable'];
        
        if (isSelected) {
          const mapping = state.selectedWords.get(word.toLowerCase());
          classes.push(mapping.replacement ? 'word-mapped' : 'word-selected');
        }
        
        return `<span class="${classes.join(' ')}" data-word="${word}" data-index="${item.index}">${word}</span>`;
      }).join('');

      interactiveText.innerHTML = html;
    }

    // Handle word clicks
    function handleWordClick(event) {
      if (!event.target.classList.contains('word-selectable')) return;
      
      const word = event.target.dataset.word;
      const wordKey = word.toLowerCase();
      
      if (state.selectedWords.has(wordKey)) {
        // Deselect word
        state.selectedWords.delete(wordKey);
        updateWordHighlights(word, false);
      } else {
        // Select word
        const count = countWordOccurrences(word);
        state.selectedWords.set(wordKey, { count, replacement: '', originalWord: word });
        updateWordHighlights(word, true);
      }
      
      renderSelectedMappings();
      updateUI();
    }

    // Count occurrences of a word in text
    function countWordOccurrences(word) {
      return state.textWords.filter(item => 
        item.type === 'word' && item.content.toLowerCase() === word.toLowerCase()
      ).length;
    }

    // Update highlighting for all instances of a word
    function updateWordHighlights(word, selected) {
      const spans = interactiveText.querySelectorAll(`[data-word="${word}"]`);
      spans.forEach(span => {
        if (selected) {
          span.classList.add('word-selected');
        } else {
          span.classList.remove('word-selected', 'word-mapped');
        }
      });
    }

    // Render selected word mappings in the sidebar
    function renderSelectedMappings() {
      if (state.selectedWords.size === 0) {
        selectedMappings.innerHTML = '<p class="text-muted small">Click words in the text to create mappings</p>';
        return;
      }

      const html = Array.from(state.selectedWords.entries()).map(([wordKey, data]) => {
        const { originalWord, count, replacement } = data;
        return `
          <div class="mapping-item" data-word-key="${wordKey}">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div class="word-preview">${originalWord}</div>
              <button type="button" class="btn btn-sm btn-outline-danger remove-mapping" data-word-key="${wordKey}">×</button>
            </div>
            <div class="input-group input-group-sm">
              <span class="input-group-text">→</span>
              <input type="text" class="form-control replacement-input" 
                     name="replacement" 
                     placeholder="Enter replacement word"
                     value="${replacement}"
                     data-word-key="${wordKey}">
              <input type="hidden" name="original" value="${originalWord}">
            </div>
            <small class="text-muted">${count} occurrence${count !== 1 ? 's' : ''} in text</small>
          </div>
        `;
      }).join('');

      selectedMappings.innerHTML = html;
    }

    // Handle replacement input changes
    function handleReplacementChange(event) {
      if (!event.target.classList.contains('replacement-input')) return;
      
      const wordKey = event.target.dataset.wordKey;
      const replacement = event.target.value;
      
      if (state.selectedWords.has(wordKey)) {
        state.selectedWords.get(wordKey).replacement = replacement;
        
        // Update visual state of word in text
        const originalWord = state.selectedWords.get(wordKey).originalWord;
        const spans = interactiveText.querySelectorAll(`[data-word="${originalWord}"]`);
        spans.forEach(span => {
          if (replacement.trim()) {
            span.classList.add('word-mapped');
            span.classList.remove('word-selected');
          } else {
            span.classList.add('word-selected');
            span.classList.remove('word-mapped');
          }
        });
      }
      
      updateUI();
    }

    // Remove mapping
    function removeMapping(wordKey) {
      if (state.selectedWords.has(wordKey)) {
        const originalWord = state.selectedWords.get(wordKey).originalWord;
        state.selectedWords.delete(wordKey);
        updateWordHighlights(originalWord, false);
        renderSelectedMappings();
        updateUI();
      }
    }

    // Handle replacement input changes
    function handleReplacementChange(event) {
      if (!event.target.classList.contains('replacement-input')) return;
      
      const wordKey = event.target.dataset.wordKey;
      const replacement = event.target.value;
      
      if (state.selectedWords.has(wordKey)) {
        state.selectedWords.get(wordKey).replacement = replacement;
        
        // Update visual state of word in text
        const originalWord = state.selectedWords.get(wordKey).originalWord;
        const spans = interactiveText.querySelectorAll(`[data-word="${originalWord}"]`);
        spans.forEach(span => {
          if (replacement.trim()) {
            span.classList.add('word-mapped');
            span.classList.remove('word-selected');
          } else {
            span.classList.add('word-selected');
            span.classList.remove('word-mapped');
          }
        });
      }
      
      updateUI();
    }

    // Remove mapping
    function removeMapping(wordKey) {
      if (state.selectedWords.has(wordKey)) {
        const originalWord = state.selectedWords.get(wordKey).originalWord;
        state.selectedWords.delete(wordKey);
        updateWordHighlights(originalWord, false);
        renderSelectedMappings();
        updateUI();
      }
    }

    // Quick word selection from frequency buttons
    function handleQuickWordSelection(event) {
      const button = event.target.closest('[data-word]');
      if (!button) return;
      
      const word = button.dataset.word;
      const wordKey = word.toLowerCase();
      
      if (!state.selectedWords.has(wordKey)) {
        const count = countWordOccurrences(word);
        state.selectedWords.set(wordKey, { count, replacement: '', originalWord: word });
        updateWordHighlights(word, true);
        renderSelectedMappings();
        updateUI();
        
        // Focus the replacement input
        setTimeout(() => {
          const input = selectedMappings.querySelector(`[data-word-key="${wordKey}"] .replacement-input`);
          if (input) input.focus();
        }, 100);
      }
    }

    // Clear all selections
    function clearAllSelections() {
      state.selectedWords.clear();
      renderInteractiveText();
      renderSelectedMappings();
      updateUI();
    }

    // Toggle highlight mode
    function toggleHighlightMode() {
      state.highlightMode = !state.highlightMode;
      highlightToggle.classList.toggle('active', state.highlightMode);
      interactiveText.style.cursor = state.highlightMode ? 'crosshair' : 'text';
    }

    // Manual mapping rows management
    function addManualMappingRow() {
      const newRow = document.createElement('div');
      newRow.className = 'mapping-row mb-2';
      newRow.innerHTML = `
        <div class="input-group input-group-sm">
          <input type="text" class="form-control original-word" name="original" placeholder="Original word" />
          <span class="input-group-text">→</span>
          <input type="text" class="form-control" name="replacement" placeholder="Replacement" />
          <button type="button" class="btn btn-outline-danger" data-action="remove-manual-row" title="Remove">×</button>
        </div>
      `;
      manualMappingRows.appendChild(newRow);
      updateUI();
    }

    function removeManualMappingRow(row) {
      const rows = manualMappingRows.querySelectorAll('.mapping-row');
      if (rows.length > 1) {
        row.remove();
      } else {
        // Clear the last row instead of removing it
        row.querySelectorAll('input').forEach(input => input.value = '');
      }
      updateUI();
    }

    // Update UI state (button states, counters, etc.)
    function updateUI() {
      const selectedCount = state.selectedWords.size;
      const manualCount = Array.from(manualMappingRows.querySelectorAll('.original-word'))
        .filter(input => input.value.trim()).length;
      
      const totalMappings = selectedCount + manualCount;
      const hasValidMappings = Array.from(state.selectedWords.values())
        .some(data => data.replacement.trim()) || manualCount > 0;
      
      generateBtn.disabled = !hasValidMappings;
      mappingCount.textContent = `${totalMappings} mapping${totalMappings !== 1 ? 's' : ''} defined`;
      
      clearSelections.disabled = selectedCount === 0;
    }

    // Event listeners
    if (interactiveText) {
      interactiveText.addEventListener('click', handleWordClick);
      initializeInteractiveText();
    }

    if (selectedMappings) {
      selectedMappings.addEventListener('input', handleReplacementChange);
      selectedMappings.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-mapping')) {
          const wordKey = event.target.dataset.wordKey;
          removeMapping(wordKey);
        }
      });
    }

    if (suggestionContainer) {
      suggestionContainer.addEventListener('click', handleQuickWordSelection);
    }

    if (highlightToggle) {
      highlightToggle.addEventListener('click', toggleHighlightMode);
    }

    if (clearSelections) {
      clearSelections.addEventListener('click', clearAllSelections);
    }

    // Manual mapping row management
    document.addEventListener('click', (event) => {
      if (event.target.matches('[data-action="add-manual-row"]')) {
        addManualMappingRow();
      }
      if (event.target.matches('[data-action="remove-manual-row"]')) {
        removeManualMappingRow(event.target.closest('.mapping-row'));
      }
    });

    // Monitor manual input changes
    if (manualMappingRows) {
      manualMappingRows.addEventListener('input', updateUI);
    }

    // Initialize
    renderSelectedMappings();
    updateUI();
  });
})();
