try {
  document.documentElement.classList.toggle(
    "dark",
    localStorage.getItem("ledger-theme") !== "light",
  );
} catch {
  /* Dark is the default even when storage is disabled. */
}
