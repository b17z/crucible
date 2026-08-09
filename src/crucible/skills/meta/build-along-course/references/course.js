/* Build-Along Course — base script.
 * Original to crucible. Vanilla JS, zero dependencies, no build step,
 * no external requests. Copied verbatim into course/course.js at
 * scaffold time — never regenerate, never hand-edit a scaffolded copy.
 *
 * Three independent features, each degrading gracefully if its markup
 * isn't present on the page:
 *   1. Scroll-spy nav dots (click-to-scroll + highlight-on-scroll)
 *   2. Quiz check/reveal
 *   3. Glossary tooltips (keyboard focus, in addition to CSS :hover)
 */
(function () {
  "use strict";

  /* ---- 1. Nav dots: click-to-scroll + scroll-spy ---- */

  function initNavDots() {
    var dots = document.querySelectorAll(".nav-dots a");
    if (!dots.length) return;

    var modules = [];
    for (var i = 0; i < dots.length; i++) {
      var href = dots[i].getAttribute("href") || "";
      var id = href.charAt(0) === "#" ? href.slice(1) : "";
      var section = id ? document.getElementById(id) : null;
      if (section) {
        modules.push({ dot: dots[i], section: section });
      }
    }
    if (!modules.length) return;

    function setActive(dot) {
      for (var j = 0; j < modules.length; j++) {
        if (modules[j].dot === dot) {
          modules[j].dot.classList.add("active");
        } else {
          modules[j].dot.classList.remove("active");
        }
      }
    }

    // Click-to-scroll is native <a href="#id"> behavior; we only need
    // to mark the clicked dot active immediately (scroll-spy will
    // confirm it once the section settles into view).
    for (var k = 0; k < modules.length; k++) {
      (function (entry) {
        entry.dot.addEventListener("click", function () {
          setActive(entry.dot);
        });
      })(modules[k]);
    }

    if (typeof IntersectionObserver === "function") {
      var observer = new IntersectionObserver(
        function (entries) {
          for (var e = 0; e < entries.length; e++) {
            if (entries[e].isIntersecting) {
              for (var m = 0; m < modules.length; m++) {
                if (modules[m].section === entries[e].target) {
                  setActive(modules[m].dot);
                }
              }
            }
          }
        },
        { rootMargin: "-40% 0px -50% 0px", threshold: 0 }
      );
      for (var n = 0; n < modules.length; n++) {
        observer.observe(modules[n].section);
      }
    } else {
      // No IntersectionObserver available: click-to-scroll still
      // works; scroll-spy highlighting is simply skipped. No polyfill.
      setActive(modules[0].dot);
    }
  }

  /* ---- 2. Quizzes: check/reveal ---- */

  function initQuizzes() {
    var quizzes = document.querySelectorAll(".quiz");
    for (var i = 0; i < quizzes.length; i++) {
      initQuiz(quizzes[i]);
    }
  }

  function initQuiz(quiz) {
    var button = quiz.querySelector("button.check");
    var explanation = quiz.querySelector(".explanation");
    if (!button || !explanation) return;

    button.addEventListener("click", function () {
      var selected = quiz.querySelector('input[type="radio"]:checked');
      var resultEl = explanation.querySelector(".result");

      if (!selected) {
        if (resultEl) {
          resultEl.textContent = "Pick an answer first.";
          resultEl.className = "result";
        }
        explanation.classList.add("visible");
        explanation.classList.add("unanswered");
        return;
      }

      explanation.classList.remove("unanswered");

      var isCorrect = selected.hasAttribute("data-correct");
      if (resultEl) {
        resultEl.textContent = isCorrect ? "Correct." : "Not quite.";
        resultEl.className = "result " + (isCorrect ? "correct" : "incorrect");
      }
      explanation.classList.add("visible");
    });
  }

  /* ---- 3. Glossary tooltips: keyboard accessibility ---- */

  // CSS already shows .tip on :hover/:focus/:focus-visible. This just
  // makes sure Escape can dismiss a focus-triggered tip without
  // requiring the user to tab away, and that touch taps toggle it.
  function initTooltips() {
    var terms = document.querySelectorAll(".term");
    for (var i = 0; i < terms.length; i++) {
      (function (term) {
        term.addEventListener("keydown", function (event) {
          if (event.key === "Escape") {
            term.blur();
          }
        });
        term.addEventListener("click", function (event) {
          // Touch devices have no :hover; toggle a class instead.
          event.preventDefault();
          term.classList.toggle("tip-open");
          var tip = term.querySelector(".tip");
          if (tip) {
            tip.style.opacity = term.classList.contains("tip-open") ? "1" : "";
            tip.style.pointerEvents = term.classList.contains("tip-open")
              ? "auto"
              : "";
          }
        });
      })(terms[i]);
    }
  }

  function init() {
    initNavDots();
    initQuizzes();
    initTooltips();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
