/* Navigation toggle (mobile hamburger menu) */
(function () {
    "use strict";

    var toggle = document.getElementById("nav-toggle");
    var menu = document.getElementById("nav-menu");

    if (!toggle || !menu) return;

    toggle.addEventListener("click", function () {
        var expanded = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", String(!expanded));
        menu.classList.toggle("open");

        /* Update hamburger icon */
        if (!expanded) {
            toggle.querySelector(".hamburger").style.background = "transparent";
        } else {
            toggle.querySelector(".hamburger").style.background = "";
        }
    });

    /* Close menu when clicking a link */
    var links = menu.querySelectorAll(".nav-link");
    for (var i = 0; i < links.length; i++) {
        links[i].addEventListener("click", function () {
            menu.classList.remove("open");
            toggle.setAttribute("aria-expanded", "false");
            toggle.querySelector(".hamburger").style.background = "";
        });
    }

    /* Close menu on Escape */
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && menu.classList.contains("open")) {
            menu.classList.remove("open");
            toggle.setAttribute("aria-expanded", "false");
            toggle.querySelector(".hamburger").style.background = "";
            toggle.focus();
        }
    });
})();
