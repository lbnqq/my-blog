document.addEventListener("DOMContentLoaded", () => {
  const menuButton = document.querySelector("[data-menu-toggle]");
  const mobileMenu = document.querySelector("[data-mobile-menu]");

  if (menuButton && mobileMenu) {
    menuButton.addEventListener("click", () => {
      const isOpen = mobileMenu.classList.toggle("is-open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
    });

    mobileMenu.querySelectorAll("a, button").forEach((control) => {
      control.addEventListener("click", () => {
        mobileMenu.classList.remove("is-open");
        menuButton.setAttribute("aria-expanded", "false");
      });
    });
  }

  document.querySelectorAll(".star-input").forEach((group) => {
    const radios = Array.from(group.querySelectorAll('input[type="radio"]'));
    const paint = () => {
      const selected = radios.find((radio) => radio.checked);
      const selectedValue = selected ? Number(selected.value) : 0;
      group.querySelectorAll("label").forEach((label) => {
        const input = label.querySelector('input[type="radio"]');
        label.classList.toggle("is-selected", Number(input.value) <= selectedValue);
      });
    };

    radios.forEach((radio) => radio.addEventListener("change", paint));
    paint();
  });

  const ratingForm = document.querySelector("[data-rating-form]");
  if (ratingForm) {
    const counter = document.querySelector("[data-rated-count]");
    const progress = document.querySelector("[data-rating-progress]");
    const groups = Array.from(ratingForm.querySelectorAll(".star-input"));
    const updateProgress = () => {
      const rated = groups.filter((group) => group.querySelector('input[type="radio"]:checked')).length;
      if (counter) counter.textContent = String(rated);
      if (progress) progress.style.width = `${Math.min(rated / 8, 1) * 100}%`;
    };

    ratingForm.addEventListener("change", updateProgress);
    updateProgress();
  }
});
