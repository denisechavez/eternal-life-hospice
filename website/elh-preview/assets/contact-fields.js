// Contact syntax checks complement, but do not replace, server spam protection.
export function validPhone(value) {
  const digits = value.replace(/\D/g, "");
  return /^[+]?[0-9().\s-]+$/.test(value) &&
    (value.startsWith("+1") ? digits.length === 11 :
      value.startsWith("+") ? digits.length >= 10 && digits.length <= 15 :
      digits.length === 10 || (digits.length === 11 && digits[0] === "1"));
}

export function formatPhone(value) {
  if (!/^[+]?[0-9().\s-]*$/.test(value)) return value;
  const digits = value.replace(/\D/g, "");
  const country = (digits.length === 11 && digits[0] === "1") || value.startsWith("+1");
  // Preserve other international numbers; never truncate or change country codes.
  if ((value.startsWith("+") && !country) || digits.length > (country ? 11 : 10)) return value;
  const local = country ? digits.slice(1) : digits;
  return (country ? "+1 " : "") + local.slice(0, 3) +
    (local.length > 3 ? "." + local.slice(3, 6) : "") +
    (local.length > 6 ? "." + local.slice(6) : "");
}

function configure(input) {
  if (input.type === "tel") {
    input.setAttribute("inputmode", "tel");
    input.setAttribute("autocomplete", "tel");
  } else if (input.type === "email") {
    input.setAttribute("inputmode", "email");
    input.setAttribute("autocomplete", "email");
    // Native email inputs alone accept addresses with no domain suffix.
    input.setAttribute("pattern", "[^\\s@]+@[^\\s@]+\\.[^\\s@]+");
    input.setAttribute("autocapitalize", "none");
    input.spellcheck = false;
  }
}

function update(input, format) {
  configure(input);
  if (input.type === "tel") {
    if (format) {
      const before = input.value;
      const caret = input.selectionStart;
      const digitsBefore = caret === null ? null : before.slice(0, caret).replace(/\D/g, "").length;
      const formatted = formatPhone(before);
      if (formatted !== before) input.value = formatted;
      if (digitsBefore !== null && formatted !== before) {
        let position = 0, count = 0;
        while (position < input.value.length && count < digitsBefore) {
          if (/\d/.test(input.value[position])) count++;
          position++;
        }
        input.setSelectionRange(position, position);
      }
    }
    input.setCustomValidity(!input.value || validPhone(input.value) ? "" :
      "Please enter a complete 10-digit phone number, or an international number beginning with +.");
  } else if (input.type === "email") {
    input.setCustomValidity(!input.value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value) ? "" :
      "Please enter an email address such as name@example.com.");
  }
}

export function install(root = document) {
  root.querySelectorAll('input[type="tel"],input[type="email"]').forEach(input => update(input, false));
  const contact = input => input && input.tagName === "INPUT" && /^(tel|email)$/.test(input.type);
  root.addEventListener("focusin", event => {
    if (contact(event.target)) update(event.target, false);
  });
  root.addEventListener("input", event => {
    if (contact(event.target)) update(event.target, true);
  });
  root.addEventListener("focusout", event => {
    if (contact(event.target)) {
      event.target.value = event.target.value.trim();
      update(event.target, true);
    }
  });
}
