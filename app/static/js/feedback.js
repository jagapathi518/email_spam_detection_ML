/**
 * SpamGuard AI — Feedback Form Handler
 * Submits anonymous feedback to /api/feedback without storing email text.
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('feedback-form');
    const statusMsg = document.getElementById('feedback-status');
    const submitBtn = document.getElementById('btn-submit-feedback');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const feedbackType = document.getElementById('feedback-type').value;
        const actualLabel = document.getElementById('actual-label').value;
        const rating = document.getElementById('rating').value;
        const userNotes = document.getElementById('user-notes').value.trim();

        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
        statusMsg.style.display = 'none';

        try {
            const resp = await fetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    feedback_type: feedbackType,
                    actual_label: actualLabel || null,
                    rating: rating ? parseInt(rating, 10) : null,
                    user_notes: userNotes || null
                })
            });

            if (resp.ok) {
                statusMsg.textContent = 'Thank you! Your feedback has been recorded anonymously.';
                statusMsg.className = 'feedback-success';
                statusMsg.style.display = 'block';
                form.reset();
            } else {
                statusMsg.textContent = 'Could not submit feedback at this time. Please try again.';
                statusMsg.className = 'feedback-error';
                statusMsg.style.display = 'block';
            }
        } catch (err) {
            statusMsg.textContent = 'Network error while submitting feedback.';
            statusMsg.className = 'feedback-error';
            statusMsg.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Feedback';
        }
    });
});
