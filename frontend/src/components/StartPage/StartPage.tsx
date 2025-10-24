import React from "react";
import "./StartPage.css";

const StartPage: React.FC = () => {
  const [range, setRange] = React.useState("month");
  const [customStart, setCustomStart] = React.useState("");
  const [customEnd, setCustomEnd] = React.useState("");

  // Typewriter effect logic
  const phrases = ["exams", "homework", "assignments", "projects", "school"];
  const [currentPhrase, setCurrentPhrase] = React.useState(0);
  const [displayText, setDisplayText] = React.useState("");
  const [deleting, setDeleting] = React.useState(false);

  React.useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const fullText = `Let's ace our ${phrases[currentPhrase]}.`;
    const staticLength = `Let's ace our `.length;
    if (!deleting && displayText.length < fullText.length) {
      timeout = setTimeout(() => {
        setDisplayText(fullText.slice(0, displayText.length + 1));
      }, 110);
    } else if (deleting && displayText.length > staticLength) {
      timeout = setTimeout(() => {
        setDisplayText(fullText.slice(0, displayText.length - 1));
      }, 65);
    } else if (!deleting && displayText.length === fullText.length) {
      timeout = setTimeout(() => setDeleting(true), 1100);
    } else if (deleting && displayText.length === staticLength) {
      timeout = setTimeout(() => {
        setDeleting(false);
        setCurrentPhrase((prev) => (prev + 1) % phrases.length);
      }, 500);
    }
    return () => clearTimeout(timeout);
  }, [displayText, deleting, currentPhrase, phrases]);

  // Prompt options logic
  const promptOptions = [
    { label: "Summarize these", value: "summarize" },
    { label: "What is this assignment on?", value: "what" },
    { label: "Suggest study plan", value: "plan" },
    { label: "Custom", value: "custom" },
  ];
  const [selectedPrompt, setSelectedPrompt] = React.useState<string | null>(
    null
  );
  const [customPrompt, setCustomPrompt] = React.useState("");

  // Button enable logic
  const isDateValid =
    (range === "custom" ? customStart && customEnd : !!range) && range !== "";
  const isPromptValid =
    selectedPrompt &&
    (selectedPrompt !== "custom" ||
      (selectedPrompt === "custom" && customPrompt.trim() !== ""));
  const canStart = isDateValid && isPromptValid;

  return (
    <div className="startpage-container">
      <div className="startpage-box">
        <form className="startpage-form">
          <div className="startpage-typewriter">
            {displayText}
            <span className="startpage-cursor">|</span>
          </div>
          <label htmlFor="range-select" className="startpage-label">
            Summarize for:
          </label>
          <div className="startpage-select-wrapper">
            <select
              id="range-select"
              className="startpage-select"
              value={range}
              onChange={(e) => setRange(e.target.value)}
            >
              <option value="month">This Month</option>
              <option value="week">This Week</option>
              <option value="today">Today</option>
              <option value="custom">Custom Range</option>
            </select>
          </div>

          {range === "custom" && (
            <div className="startpage-custom-range">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="startpage-date"
                placeholder="Start date"
              />
              <span style={{ margin: "0 0.5rem" }}>to</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="startpage-date"
                placeholder="End date"
              />
            </div>
          )}

          {/* Prompt options buttons */}
          <div className="startpage-prompt-options">
            {promptOptions.map((opt) => (
              <button
                type="button"
                key={opt.value}
                onClick={() => setSelectedPrompt(opt.value)}
                className={`startpage-prompt-btn${
                  selectedPrompt === opt.value ? " selected" : ""
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Show custom input if custom is selected */}
          {selectedPrompt === "custom" && (
            <div
              className={`startpage-custom-input${
                range === "custom" ? " both-custom-active" : ""
              }`}
            >
              <input
                type="text"
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Type your custom prompt..."
                className="startpage-custom-input-field"
              />
            </div>
          )}

          {/* Start Summarizing button */}
          <button
            type="button"
            className={`startpage-submit-btn${canStart ? " enabled" : ""}`}
            disabled={!canStart}
            style={{
              marginTop: "2.2rem",
              width: "100%",
              padding: "0.9rem 0",
              fontSize: "1.15rem",
              fontWeight: 700,
              borderRadius: "0.7rem",
              border: "none",
              background: canStart
                ? "linear-gradient(90deg, #c52d43 0%, #e74c3c 100%)"
                : "#e0e0e0",
              color: canStart ? "#fff" : "#aaa",
              cursor: canStart ? "pointer" : "not-allowed",
              boxShadow: canStart ? "0 2px 12px #c52d4340" : "0 1px 4px #8882",
              opacity: canStart ? 1 : 0.7,
              letterSpacing: "1px",
              transition: "all 0.18s",
            }}
          >
            Start Summarizing
          </button>
        </form>
      </div>
    </div>
  );
};

export default StartPage;
