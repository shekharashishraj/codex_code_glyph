(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const rowsContainer = document.getElementById("mapping-rows");
    if (!rowsContainer) {
      return;
    }

    const templateRow = rowsContainer.querySelector(".mapping-row").cloneNode(true);
    templateRow.querySelectorAll("input").forEach((input) => {
      input.value = "";
    });

    function renumberRows() {
      rowsContainer.querySelectorAll(".mapping-row").forEach((row, index) => {
        const originalInput = row.querySelector(".original-word");
        const replacementInput = row.querySelector('input[name="replacement"]');
        if (originalInput) {
          originalInput.id = `original-${index}`;
        }
        if (replacementInput) {
          replacementInput.id = `replacement-${index}`;
        }
      });
    }

    function addRow(original = "", replacement = "") {
      const clone = templateRow.cloneNode(true);
      const originalInput = clone.querySelector(".original-word");
      const replacementInput = clone.querySelector('input[name="replacement"]');
      if (originalInput) {
        originalInput.value = original;
      }
      if (replacementInput) {
        replacementInput.value = replacement;
      }
      rowsContainer.appendChild(clone);
      renumberRows();
      return clone;
    }

    function clearRow(row) {
      row.querySelectorAll("input").forEach((input) => {
        input.value = "";
      });
    }

    document.querySelector('[data-action="add-row"]').addEventListener("click", () => {
      addRow();
    });

    rowsContainer.addEventListener("click", (event) => {
      const trigger = event.target.closest('[data-action="remove-row"]');
      if (!trigger) {
        return;
      }
      const rows = rowsContainer.querySelectorAll(".mapping-row");
      const row = trigger.closest(".mapping-row");
      if (rows.length <= 1) {
        clearRow(row);
        return;
      }
      row.remove();
      renumberRows();
    });

    const suggestionContainer = document.querySelector('[data-role="word-suggestions"]');
    if (suggestionContainer) {
      suggestionContainer.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-word]");
        if (!button) {
          return;
        }
        const word = button.getAttribute("data-word");
        let targetRow = Array.from(rowsContainer.querySelectorAll(".mapping-row"))
          .find((row) => row.querySelector(".original-word").value.trim() === "");
        if (!targetRow) {
          targetRow = addRow();
        }
        const originalInput = targetRow.querySelector(".original-word");
        if (originalInput) {
          originalInput.value = word;
        }
        const replacementInput = targetRow.querySelector('input[name="replacement"]');
        if (replacementInput) {
          replacementInput.focus();
        }
      });
    }

    renumberRows();
  });
})();
