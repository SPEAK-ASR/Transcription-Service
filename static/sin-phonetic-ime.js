// Sinhala Phonetic IME (self-contained)
// - Toggle above the textarea enables/disables this IME (default OFF)
// - Inline chip inside the textarea toggles Sinhala/English while IME is ON
// - Hotkey: Ctrl+Space toggles Sinhala/English while IME is ON
// - Pasting is left as-is (no transliteration)

(function () {
  const HAL = "්"; // virama
  const ZWJ = "\u200D"; // zero-width joiner for yansaya/rakaransaya

  const VOWEL_SIGNS = {
    "": "",
    "a": "",
    "aa": "ා",
    "A": "ැ",
    "AA": "ෑ",
    "Aa": "ෑ",
    "i": "ි",
    "ii": "ී",
    "u": "ු",
    "uu": "ූ",
    "R": "ෘ",
    "Ru": "ෲ",
    "e": "ෙ",
    "ee": "ේ",
    "ai": "ෛ",
    "o": "ො",
    "oo": "ෝ",
    "au": "ෞ",
    "ou": "ෞ",
  };

  const INDEP_VOWELS = {
    "a": "අ",
    "aa": "ආ",
    "A": "ඇ",
    "AA": "ඈ",
    "Aa": "ඈ",
    "i": "ඉ",
    "ii": "ඊ",
    "u": "උ",
    "uu": "ඌ",
    "R": "ඍ",
    "Ru": "ඎ",
    "e": "එ",
    "ee": "ඒ",
    "ai": "ඓ",
    "o": "ඔ",
    "oo": "ඕ",
    "au": "ඖ",
    "ou": "ඖ",
  };

  // Consonants (longest-first keys for greedy parsing)
  const CONS_MAP = {
    // Aspirates and multi-char first
    "chh": "ඡ",
    "thh": "ථ",
    "dhh": "ධ",
    "kh": "ඛ",
    "gh": "ඝ",
    "ph": "ඵ",
    "bh": "භ",
    // Retroflex aspirates via capital
    "Th": "ඨ",
    "Dh": "ඪ",
    // Basic digraphs
    "ch": "ච",
    "sh": "ශ",
    "Sh": "ෂ",
    // Alveolar vs retroflex distinctions
    "th": "ත", // alveolar
    "dh": "ද", // alveolar
    // Singles and capitals
    "T": "ඨ",
    "D": "ඪ",
    "N": "ණ",
    "L": "ළ",
    "S": "ෂ",
    // Basic singles
    "k": "ක",
    "g": "ග",
    "j": "ජ",
    "t": "ට", // retroflex
    "d": "ඩ", // retroflex
    "p": "ප",
    "b": "බ",
    "m": "ම",
    "n": "න",
    "y": "ය",
    "r": "ර",
    "l": "ල",
    "w": "ව",
    "v": "ව",
    "s": "ස",
    "h": "හ",
    "f": "ෆ",
    "q": "ද", // alias
  };

  // Special nasal/other clusters provided
  const SPECIAL_CLUSTERS = [
    { key: "zga", val: "ඟ" },
    { key: "zja", val: "ඦ" },
    { key: "zda", val: "ඬ" },
    { key: "zdha", val: "ඳ" },
    { key: "zqa", val: "ඳ" },
    { key: "zka", val: "ඤ" },
    { key: "zha", val: "ඥ" },
    { key: "Ba", val: "ඹ" },
  ];

  // Helper: longest-first keys for consonants
  const CONS_KEYS = Object.keys(CONS_MAP).sort((a, b) => b.length - a.length);

  // Vowel keys sorted by length for greedy match
  const VOW_KEYS = Object.keys(VOWEL_SIGNS).sort((a, b) => b.length - a.length);
  const INDEP_VOW_KEYS = Object.keys(INDEP_VOWELS).sort((a, b) => b.length - a.length);

  // Utility: test if char is Latin letter
  function isLatinLetter(s) {
    return /^[A-Za-z]+$/.test(s);
  }

  // Transliterate a roman token to Sinhala (greedy, best-effort)
  function transliterate(roman) {
    let out = "";
    let i = 0;

    while (i < roman.length) {
      const rest = roman.slice(i);

      // Boundaries / passthrough
      const c = roman[i];
      if (!isLatinLetter(c)) {
        // Pass through non-letters (we handle x/H/X below when letters)
        out += c; i++; continue;
      }

      // Recognize zn -> anusvara
      if (rest.startsWith('zn')) { out += "ං"; i += 2; continue; }

      // Specific clusters only requested: kya, kra
      if (rest.startsWith('kya')) { out += "ක්" + ZWJ + "ය"; i += 3; continue; } // ක්‍ය
      if (rest.startsWith('kra')) { out += "ක්" + ZWJ + "ර"; i += 3; continue; } // ක්‍ර

      // Special nasal/other clusters
      let matched = false;
      for (const sc of SPECIAL_CLUSTERS) {
        if (rest.startsWith(sc.key)) {
          out += sc.val;
          i += sc.key.length;
          matched = true;
          break;
        }
      }
      if (matched) continue;

      // Handle single-letter specials first
      if (c === 'x') { out += "ං"; i += 1; continue; }
      if (c === 'X') { out += "ඞ"; i += 1; continue; }
      if (c === 'H') { out += "ඃ"; i += 1; continue; }

      // Consonant + vowel
      let consKey = null;
      for (const k of CONS_KEYS) {
        if (rest.startsWith(k)) { consKey = k; break; }
      }

      if (consKey) {
        const base = CONS_MAP[consKey];
        i += consKey.length;
        const after = roman.slice(i);

        // Try to match longest vowel following
        let vPat = null;
        for (const vk of VOW_KEYS) {
          if (vk && after.startsWith(vk)) { vPat = vk; break; }
        }
        // Accept empty vowel only if explicitly 'a' follows or none matches
        if (vPat) {
          i += vPat.length;
          const sign = VOWEL_SIGNS[vPat] || "";
          if (sign) out += base + sign; else out += base; // 'a' maps to inherent
        } else {
          // No vowel matched, check for single-letter vowels
          // If the next char is 'a' handle as inherent
          if (after.startsWith('a')) {
            i += 1; // consume 'a'
            out += base; // inherent 'a'
          } else {
            out += base + HAL; // bare consonant
          }
        }
        continue;
      }

      // Independent vowels
      let vKey = null;
      for (const vk of INDEP_VOW_KEYS) {
        if (rest.startsWith(vk)) { vKey = vk; break; }
      }
      if (vKey) {
        out += INDEP_VOWELS[vKey];
        i += vKey.length;
        continue;
      }

      // Fallback: pass-through
      out += c;
      i += 1;
    }

    return out;
  }

  // IME controller
  function attachIME(textarea, opts = {}) {
    const chip = document.getElementById('imeChip');
    const toggle = document.getElementById('imeToggle');

    const state = {
      enabled: false,
      mode: 'en', // 'si' | 'en'
      segmentStart: null,
      romanBuffer: '',
      lastOutLen: 0,
    };

    function updateChip() {
      if (!chip) return;
      chip.disabled = !state.enabled;
      if (!state.enabled) {
        chip.classList.remove('si-active');
        chip.textContent = 'සි | en';
        return;
      }
      if (state.mode === 'si') {
        chip.classList.add('si-active');
        chip.textContent = 'සි | en';
      } else {
        chip.classList.remove('si-active');
        chip.textContent = 'si | EN';
      }
    }

    function finalizeSegment() {
      state.segmentStart = null;
      state.romanBuffer = '';
      state.lastOutLen = 0;
    }

    function replaceRange(start, end, insert) {
      const val = textarea.value;
      textarea.value = val.slice(0, start) + insert + val.slice(end);
      textarea.selectionStart = textarea.selectionEnd = start + insert.length;
    }

    function applyInput(str) {
      // Anchor segmentStart if needed or if caret moved
      const caret = textarea.selectionStart;
      const segEnd = state.segmentStart != null ? state.segmentStart + state.lastOutLen : null;
      const atSegEnd = segEnd === caret;
      if (state.segmentStart == null || !atSegEnd) {
        finalizeSegment();
        state.segmentStart = caret;
      }

      state.romanBuffer += str;
      const nextOut = transliterate(state.romanBuffer);
      const start = state.segmentStart;
      const end = start + state.lastOutLen;
      replaceRange(start, end, nextOut);
      state.lastOutLen = nextOut.length;
    }

    function handleBackspace(e) {
      // Only handle when composing and caret at end
      const caret = textarea.selectionStart;
      const segEnd = state.segmentStart != null ? state.segmentStart + state.lastOutLen : null;
      if (state.segmentStart != null && caret === segEnd && state.romanBuffer.length > 0) {
        e.preventDefault();
        state.romanBuffer = state.romanBuffer.slice(0, -1);
        const nextOut = transliterate(state.romanBuffer);
        const start = state.segmentStart;
        const end = start + state.lastOutLen;
        replaceRange(start, end, nextOut);
        state.lastOutLen = nextOut.length;
        if (state.romanBuffer.length === 0) finalizeSegment();
      } else {
        finalizeSegment(); // if editing elsewhere, drop composition
      }
    }

    // Event bindings
    textarea.addEventListener('beforeinput', (e) => {
      if (!state.enabled || state.mode !== 'si') return;
      if (e.inputType === 'insertFromPaste' || e.inputType === 'insertFromDrop') {
        finalizeSegment();
        return; // do not transliterate pasted text
      }
      if (e.inputType === 'insertText' && typeof e.data === 'string' && e.data.length > 0) {
        // Letters only; numbers/punct pass-through
        if (/^[A-Za-z]+$/.test(e.data)) {
          e.preventDefault();
          applyInput(e.data);
        } else {
          finalizeSegment();
        }
      } else if (e.inputType && e.inputType.startsWith('delete')) {
        // backspace/delete handled in keydown for better control
      } else {
        finalizeSegment();
      }
    });

    textarea.addEventListener('keydown', (e) => {
      // Ctrl+Space flips si/en when IME is enabled
      if (state.enabled && e.ctrlKey && !e.shiftKey && !e.altKey && e.code === 'Space') {
        e.preventDefault();
        state.mode = state.mode === 'si' ? 'en' : 'si';
        updateChip();
        finalizeSegment();
        return;
      }
      if (!state.enabled || state.mode !== 'si') return;

      // Handle backspace during composition
      if (e.key === 'Backspace') {
        return handleBackspace(e);
      }

      // Finalize on boundaries/punct
      if (e.key === 'Enter' || e.key === 'Tab' || e.key === ' ') {
        finalizeSegment();
        return; // allow default
      }
      if (/^[.,;:!?\-()\[\]{}"'\/\\]$/.test(e.key)) {
        finalizeSegment();
        return; // let punctuation through
      }

      // Caret navigation ends composition
      if (["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","Home","End","PageUp","PageDown"].includes(e.key)) {
        finalizeSegment();
        return;
      }
    });

    // Chip click toggles si/en
    if (chip) {
      chip.addEventListener('click', () => {
        if (!state.enabled) return;
        state.mode = state.mode === 'si' ? 'en' : 'si';
        updateChip();
        finalizeSegment();
        textarea.focus();
      });
    }

    // Toggle enable/disable IME
    if (toggle) {
      toggle.addEventListener('change', () => {
        state.enabled = !!toggle.checked;
        state.mode = state.enabled ? 'si' : 'en';
        updateChip();
        finalizeSegment();
        textarea.focus();
      });
    }

    // Initialize visuals
    updateChip();

    return {
      get enabled() { return state.enabled; },
      set enabled(v) { state.enabled = !!v; updateChip(); finalizeSegment(); },
      get mode() { return state.mode; },
      set mode(v) { state.mode = v === 'si' ? 'si' : 'en'; updateChip(); finalizeSegment(); },
      detach() { /* no-op for now */ },
    };
  }

  // Auto-attach on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', () => {
    const ta = document.getElementById('transcription');
    if (ta) attachIME(ta);
  });

  // Expose API for debugging/testing
  window.SinPhoneticIME = { attach: attachIME };
})();
