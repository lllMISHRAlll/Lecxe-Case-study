import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ChartSpec, ChartType } from "@/lib/types";
import { ChartView } from "./ChartView";

function spec(type: ChartType): ChartSpec {
  if (type === "scatter") {
    return {
      type,
      title: "Price vs quantity",
      x: "quantity",
      y: ["price"],
      data: [
        { quantity: 10, price: 100 },
        { quantity: 20, price: 80 },
      ],
    };
  }
  return {
    type,
    title: "Spend by vendor",
    x: "vendor",
    y: ["spend_inr"],
    data: [
      { vendor: "Zenith", spend_inr: 12650 },
      { vendor: "Anand", spend_inr: 9000 },
    ],
  };
}

describe("ChartView", () => {
  it.each<ChartType>(["bar", "horizontal_bar", "line", "pie", "scatter"])(
    "FE-13 renders a %s chart from its spec",
    (type) => {
      const { container } = render(<ChartView spec={spec(type)} width={600} height={300} />);
      expect(screen.getByTestId(`chart-${type}`)).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: spec(type).title })).toBeInTheDocument();
      expect(container.querySelector(".recharts-surface")).not.toBeNull();
    },
  );

  it("draws nothing for a table-only result", () => {
    const { container } = render(<ChartView spec={spec("table")} width={600} height={300} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("fills the available width when no size is given", () => {
    render(<ChartView spec={spec("bar")} />);
    expect(screen.getByTestId("chart-bar")).toBeInTheDocument();
  });
});
