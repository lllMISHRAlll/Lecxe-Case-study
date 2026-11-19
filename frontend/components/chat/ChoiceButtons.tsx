import type { Choice, ChoicesPayload } from "@/lib/types";

interface ChoiceButtonsProps {
  choices: ChoicesPayload;
  onChoose: (choice: Choice) => void;
  disabled?: boolean;
}

export function ChoiceButtons({ choices, onChoose, disabled = false }: ChoiceButtonsProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs text-muted">{choices.prompt}</p>
      <div className="flex flex-wrap gap-2">
        {choices.options.map((option) => (
          <button
            key={option.id}
            type="button"
            disabled={disabled}
            onClick={() => onChoose(option)}
            className="rounded-md border border-accent px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-50"
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
