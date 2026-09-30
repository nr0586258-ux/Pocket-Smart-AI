(() => {
  const $ = (sel, root = document) => root.querySelector(sel);

  function errorText(data) {
    if (!data) return "Something went wrong. Please try again.";
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map(d => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join("; ");
    }
    return "Something went wrong. Please try again.";
  }

  function showError(form, msg) {
    const box = $(".form-error", form);
    box.textContent = msg || "";
    box.hidden = !msg;
  }

  async function submitPlanner(form, url, buildInit) {
    const btn = $("button[type=submit]", form);
    const label = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Planning...";
    showError(form, "");
    try {
      const res = await fetch(url, { method: "POST", credentials: "same-origin", ...buildInit() });
      if (res.status === 401) { window.location.href = "/login"; return; }
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(errorText(data));
      window.location.href = "/recommendations/" + data.history_id;
    } catch (err) {
      showError(form, err.message);
      btn.disabled = false;
      btn.textContent = label;
    }
  }

  const num = (form, name) => parseFloat(form.elements[name].value);

  // ---- Home planner ------------------------------------------------------------
  const homeForm = $("#home-form");
  if (homeForm) {
    const rows = $("#rows");
    const addRow = (item = "", qty = 1) => {
      const node = $("#row-tpl").content.firstElementChild.cloneNode(true);
      $(".item", node).value = item;
      $(".qty", node).value = qty;
      $(".remove", node).addEventListener("click", () => {
        if (rows.children.length > 1) node.remove();
      });
      rows.appendChild(node);
    };
    addRow("Lights", 3);
    addRow("Ceiling fan", 2);
    $("#add-row").addEventListener("click", () => addRow());

    homeForm.addEventListener("submit", e => {
      e.preventDefault();
      const items = [...rows.children].map(r => ({
        room: $(".room", r).value,
        item: $(".item", r).value.trim(),
        quantity: parseInt($(".qty", r).value, 10) || 1,
      })).filter(i => i.item);
      if (!(num(homeForm, "budget") > 0)) return showError(homeForm, "Enter a budget greater than 0.");
      if (!items.length) return showError(homeForm, "Add at least one item.");
      submitPlanner(homeForm, "/generate-home", () => ({
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          budget: num(homeForm, "budget"),
          style: homeForm.elements.style.value,
          notes: homeForm.elements.notes.value,
          items,
        }),
      }));
    });
  }

  // ---- Party planner -----------------------------------------------------------
  const partyForm = $("#party-form");
  if (partyForm) {
    partyForm.addEventListener("submit", e => {
      e.preventDefault();
      if (!(num(partyForm, "budget") > 0)) return showError(partyForm, "Enter a budget greater than 0.");
      const guests = parseInt(partyForm.elements.guests.value, 10);
      if (!(guests >= 1)) return showError(partyForm, "Enter the number of guests.");
      submitPlanner(partyForm, "/generate-party", () => ({
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          budget: num(partyForm, "budget"),
          guests,
          event_type: partyForm.elements.event_type.value,
          venue: partyForm.elements.venue.value,
          city: partyForm.elements.city.value,
          needs_stay: partyForm.elements.needs_stay.checked,
          notes: partyForm.elements.notes.value,
        }),
      }));
    });
  }

  // ---- Jewelry planner ---------------------------------------------------------
  const jewelryForm = $("#jewelry-form");
  if (jewelryForm) {
    const fileInput = $("#outfit");
    const preview = $("#preview");
    fileInput.addEventListener("change", () => {
      const f = fileInput.files[0];
      if (f) { preview.src = URL.createObjectURL(f); preview.hidden = false; } else { preview.hidden = true; }
    });
    jewelryForm.addEventListener("submit", e => {
      e.preventDefault();
      if (!(num(jewelryForm, "budget") > 0)) return showError(jewelryForm, "Enter a budget greater than 0.");
      const f = fileInput.files[0];
      if (f && f.size > 5 * 1024 * 1024) return showError(jewelryForm, "Image is larger than 5 MB.");
      const fd = new FormData(jewelryForm);
      if (!f) fd.delete("outfit_image");
      submitPlanner(jewelryForm, "/generate-jewelry", () => ({ body: fd }));
    });
  }
})();
