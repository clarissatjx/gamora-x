export default function Pill({ text, color }) {
  return (
    <span
      className="pill"
      style={{
        color,
        border: `1px solid color-mix(in srgb, ${color} 30%, transparent)`,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
      }}
    >
      {text}
    </span>
  );
}
