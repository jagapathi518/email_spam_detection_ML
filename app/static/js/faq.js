/* FAQ accordion toggle */
(function () {
    "use strict";

    var faqItems = document.querySelectorAll(".faq-item");

    for (var i = 0; i < faqItems.length; i++) {
        var question = faqItems[i].querySelector(".faq-question");
        if (question) {
            question.addEventListener("click", handleFaqClick);
        }
    }

    function handleFaqClick() {
        var item = this.closest(".faq-item");
        var answer = item.querySelector(".faq-answer");
        var isOpen = item.classList.contains("open");

        /* Close all other items */
        for (var j = 0; j < faqItems.length; j++) {
            faqItems[j].classList.remove("open");
            var ans = faqItems[j].querySelector(".faq-answer");
            if (ans) {
                ans.setAttribute("aria-hidden", "true");
            }
            var q = faqItems[j].querySelector(".faq-question");
            if (q) {
                q.setAttribute("aria-expanded", "false");
            }
        }

        /* Toggle current item */
        if (!isOpen) {
            item.classList.add("open");
            if (answer) answer.setAttribute("aria-hidden", "false");
            this.setAttribute("aria-expanded", "true");
        }
    }
})();
