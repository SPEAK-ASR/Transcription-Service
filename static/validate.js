(() => {
    const API_BASE = '/api/v1/validation';

    document.addEventListener('DOMContentLoaded', () => {
        const form = document.getElementById('transcriptionForm');
        if (!form) {
            return;
        }

        // // Ensure reference section is hidden by default on page load
        // const referenceSection = document.getElementById('referenceSection');
        // if (referenceSection) {
        //     referenceSection.style.display = 'none';
        // }

        const submitBtn = document.getElementById('validateSubmitBtn');
        const nextBtn = document.getElementById('fetchNextBtn');

        const initialData = typeof window.initialValidationItem === 'string'
            ? (window.initialValidationItem === 'null' ? null : JSON.parse(window.initialValidationItem))
            : window.initialValidationItem;

        applyValidationItem(initialData);

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (!form.dataset.transcriptionId) {
                showNotification('No transcription selected for validation.', 'error');
                return;
            }

            try {
                toggleLoadingState(true);
                const payload = buildPayloadFromForm(form);
                const transId = form.dataset.transcriptionId;
                const response = await fetch(`${API_BASE}/${transId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    let message = 'Failed to validate transcription.';
                    try {
                        const errorBody = await response.json();
                        if (errorBody?.detail) {
                            message = errorBody.detail;
                        }
                    } catch (_) {
                        /* ignore JSON parse errors */
                    }
                    showNotification(message, 'error');
                    return;
                }

                // Show success popup similar to transcription submission
                if (typeof showSuccessPopup === 'function') {
                    showSuccessPopup('Transcription validated successfully! Loading next item...');
                } else {
                    showNotification('Transcription validated successfully.', 'success');
                }
                
                // Scroll to top of the page
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
                
                // Wait a bit before loading next item to allow popup to be seen
                setTimeout(async () => {
                    await fetchNextValidationItem(form);
                }, 2000);
            } catch (error) {
                console.error('Error validating transcription:', error);
                showNotification('Could not validate transcription. Please try again.', 'error');
            } finally {
                toggleLoadingState(false);
            }
        });

        if (nextBtn) {
            nextBtn.addEventListener('click', async () => {
                await fetchNextValidationItem(form);
                // Scroll to top when manually fetching next item
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
        }
    });

    function buildPayloadFromForm(form) {
        const data = new FormData(form);
        return {
            transcription: (data.get('transcription') || '').trim(),
            speaker_gender: data.get('speaker_gender') || '',
            has_noise: data.has('has_noise'),
            is_code_mixed: data.has('is_code_mixed'),
            is_speaker_overlappings_exist: data.has('is_speaker_overlapping'),
            is_audio_suitable: (data.get('is_audio_suitable') || 'true') === 'true',
        };
    }

    async function fetchNextValidationItem(form) {
        try {
            toggleLoadingState(true);
            const response = await fetch(`${API_BASE}/next`);

            if (response.status === 404) {
                showNotification('No more pending transcriptions.', 'info');
                applyValidationItem(null);
                return;
            }

            if (!response.ok) {
                throw new Error(`Unexpected status ${response.status}`);
            }

            const payload = await response.json();
            applyValidationItem(payload);
            showNotification('Loaded next transcription for validation.', 'success');
            
            // Scroll to top when new item is loaded
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        } catch (error) {
            console.error('Error fetching next validation item:', error);
            showNotification('Could not load the next transcription. Try again later.', 'error');
        } finally {
            toggleLoadingState(false);
        }
    }

    function applyValidationItem(item) {
        const form = document.getElementById('transcriptionForm');
        const workArea = document.getElementById('validationWorkArea');
        const placeholder = document.getElementById('noValidationPlaceholder');

        if (!form || !workArea || !placeholder) {
            return;
        }

        const hasItem = !!(item && item.transcription && item.audio);

        if (!hasItem) {
            form.reset();
            form.dataset.transcriptionId = '';
            handleValidationAudioSuitabilityChange({ checked: false });
            updateSummary({ audio_filename: '---', created_at: '---', is_validated: false });
            toggleAudioSection(false);
            return;
        }

        toggleAudioSection(true);

        const transcription = item.transcription;
        const audio = item.audio;

        form.dataset.transcriptionId = transcription.trans_id;

        const transcriptionField = form.querySelector('textarea[name="transcription"]');
        if (transcriptionField) {
            transcriptionField.value = transcription.transcription || '';
            transcriptionField.dispatchEvent(new Event('input'));
        }

        const speakerSelect = document.getElementById('speaker_gender');
        if (speakerSelect) {
            speakerSelect.value = transcription.speaker_gender || '';
        }

        setCheckbox('has_noise', transcription.has_noise);
        setCheckbox('is_code_mixed', transcription.is_code_mixed);
        setCheckbox('is_speaker_overlapping', transcription.is_speaker_overlappings_exist);

        const suitabilityCheckbox = document.getElementById('audioNotSuitable');
        if (suitabilityCheckbox) {
            suitabilityCheckbox.checked = transcription.is_audio_suitable === false;
        }

        // Handle reference section
        const referenceToggleSection = document.querySelector('.reference-toggle-section');
        const referenceSection = document.getElementById('referenceSection');
        const referenceText = referenceSection ? referenceSection.querySelector('.reference-text') : null;
        const toggleBtn = document.getElementById('referenceToggleBtn');
        const toggleIcon = toggleBtn ? toggleBtn.querySelector('.toggle-icon') : null;
        
        if (referenceToggleSection && referenceSection && referenceText) {
            if (audio.google_transcription) {
                referenceText.textContent = audio.google_transcription;
                referenceToggleSection.style.display = 'block';
                // Reset to collapsed state
                referenceSection.style.display = 'none';
                if (toggleIcon) toggleIcon.textContent = '▶';
                if (toggleBtn) toggleBtn.innerHTML = '<span class="toggle-icon">▶</span> Show Google Transcription Reference';
            } else {
                referenceToggleSection.style.display = 'none';
            }
        }

        updateSummary({
            audio_filename: audio.audio_filename,
            created_at: transcription.created_at,
            is_validated: transcription.is_validated,
        });

        if (typeof updatePageWithNewAudio === 'function') {
            updatePageWithNewAudio(audio);
        }
    }

    function setCheckbox(name, value) {
        const checkbox = document.querySelector(`input[name="${name}"]`);
        if (checkbox) {
            checkbox.checked = !!value;
        }
    }

    function updateSummary({ audio_filename, created_at, is_validated }) {
        const audioEl = document.getElementById('summaryAudioFilename');
        const createdEl = document.getElementById('summaryCreatedAt');
        const statusEl = document.getElementById('summaryStatus');

        if (audioEl) audioEl.textContent = audio_filename || '---';
        if (createdEl) createdEl.textContent = created_at || '---';
        if (statusEl) statusEl.textContent = is_validated ? 'Validated' : 'Pending';
    }

    function toggleAudioSection(showWorkArea) {
        const workArea = document.getElementById('validationWorkArea');
        const placeholder = document.getElementById('noValidationPlaceholder');
        const submitBtn = document.getElementById('validateSubmitBtn');

        if (workArea) {
            workArea.style.display = showWorkArea ? '' : 'none';
        }
        if (placeholder) {
            placeholder.style.display = showWorkArea ? 'none' : '';
        }
        if (submitBtn) {
            submitBtn.disabled = !showWorkArea;
        }
    }

    function toggleLoadingState(isLoading) {
        const submitBtn = document.getElementById('validateSubmitBtn');
        const nextBtn = document.getElementById('fetchNextBtn');

        if (submitBtn) {
            submitBtn.disabled = isLoading;
            submitBtn.textContent = isLoading ? 'Saving...' : 'Mark as Validated';
        }
        if (nextBtn) {
            nextBtn.disabled = isLoading;
        }
    }

    window.handleValidationAudioSuitabilityChange = function(checkbox) {
        const hiddenField = document.getElementById('audioSuitableField');
        if (hiddenField) {
            hiddenField.value = checkbox.checked ? 'false' : 'true';
        }
    };

    // Toggle reference transcription visibility
    window.toggleReferenceTranscription = function() {
        const referenceSection = document.getElementById('referenceSection');
        const toggleBtn = document.getElementById('referenceToggleBtn');
        const toggleIcon = toggleBtn ? toggleBtn.querySelector('.toggle-icon') : null;
        
        if (!referenceSection || !toggleBtn || !toggleIcon) return;
        
        const isHidden = referenceSection.style.display === 'none';
        
        if (isHidden) {
            referenceSection.style.display = 'block';
            toggleIcon.textContent = '▼';
            toggleBtn.innerHTML = toggleBtn.innerHTML.replace('Show Google Transcription Reference', 'Hide Google Transcription Reference');
        } else {
            referenceSection.style.display = 'none';
            toggleIcon.textContent = '▶';
            toggleBtn.innerHTML = toggleBtn.innerHTML.replace('Hide Google Transcription Reference', 'Show Google Transcription Reference');
        }
    };

    // Copy reference text function
    window.copyReferenceText = function() {
        const referenceText = document.querySelector('.reference-text');
        const transcriptionTextarea = document.getElementById('transcription');
        
        if (referenceText && transcriptionTextarea) {
            transcriptionTextarea.value = referenceText.textContent.trim();
            transcriptionTextarea.focus();
            transcriptionTextarea.dispatchEvent(new Event('input'));
            
            // Show notification if available
            if (typeof showNotification === 'function') {
                showNotification('Reference text copied. Please review and edit as needed.', 'info');
            }
        }
    };
})();

