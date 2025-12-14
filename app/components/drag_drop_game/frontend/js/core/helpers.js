// UI helpers - pure utility functions

export function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(Number(v) * 100).toFixed(2)}%`;
}

export function fmtInt(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toLocaleString();
}

export function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

export function formatScenarioDateTime(datetime) {
  if (!datetime) return "—";
  try {
    const [datePart, timePart] = datetime.split(" ");
    const [year, month, day] = datePart.split("-");
    const [hour, minute] = timePart.split(":");

    const date = new Date(year, month - 1, day, hour, minute);
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    const dayName = dayNames[date.getDay()];
    const monthName = monthNames[date.getMonth()];
    const dayNum = date.getDate();
    const yearNum = date.getFullYear();

    // Format time in 12-hour format
    let h = date.getHours();
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    const m = String(date.getMinutes()).padStart(2, "0");

    return `${dayName}, ${monthName} ${dayNum}, ${yearNum} · ${h}:${m} ${ampm}`;
  } catch (e) {
    return datetime;
  }
}
