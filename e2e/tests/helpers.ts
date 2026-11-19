import { execFileSync } from "node:child_process";
import { expect, type Page } from "@playwright/test";

export const USERS = {
  pm: { name: "Arjun Rao", role: "Procurement Manager", buttons: 7, first: "Open POs" },
  bo: { name: "Meera Iyer", role: "Business Owner", buttons: 6, first: "Top vendors by spend" },
  wm: { name: "Kabir Shah", role: "Warehouse Manager", buttons: 7, first: "Stock by warehouse" },
} as const;

export async function loginAs(page: Page, user: (typeof USERS)[keyof typeof USERS]) {
  await page.goto("/login");
  await page.getByRole("button", { name: `Log in as ${user.name}, ${user.role}` }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(`Hey ${user.name}, ${user.role} welcome`)).toBeVisible();
}

export async function ask(page: Page, text: string) {
  await page.locator("#chat-message").fill(text);
  await page.getByRole("button", { name: "Send" }).click();
}

export function sql(query: string): string {
  return execFileSync(
    "psql",
    ["postgresql://postgres:postgres@localhost:55432/assistant_e2e", "-tAc", query],
    { encoding: "utf8" },
  ).trim();
}
