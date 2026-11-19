import { expect, test } from "@playwright/test";
import { ask, loginAs, sql, USERS } from "./helpers";

test.describe("E2E-01 login and role buttons", () => {
  for (const user of Object.values(USERS)) {
    test(`${user.role} sees the greeting and their buttons`, async ({ page }) => {
      await loginAs(page, user);
      const buttons = page.getByLabel("Suggested questions").getByRole("button");
      await expect(buttons).toHaveCount(user.buttons);
      await expect(buttons.first()).toHaveText(user.first);
    });
  }
});

test("E2E-02 a button shows steps, SQL, table and chart, with a summary", async ({ page }) => {
  await loginAs(page, USERS.pm);
  await page.getByLabel("Suggested questions").getByRole("button", { name: "Spend by vendor" }).click();

  const results = page.getByLabel("Results");
  await expect(results.getByText("Ran the query (5 rows)")).toBeVisible();
  await expect(results.getByText(/SELECT v\.name AS vendor/)).toBeVisible();
  await expect(results.getByRole("cell", { name: "Global Automation Inc." })).toBeVisible();
  await expect(page.getByTestId("chart-horizontal_bar")).toBeVisible();
  await expect(page.getByLabel("Conversation").getByText(/Here are the results/)).toBeVisible();
});

test("E2E-03 a typed question streams an answer", async ({ page }) => {
  await loginAs(page, USERS.bo);
  await ask(page, "Which deliveries are overdue?");
  await expect(page.getByLabel("Conversation").getByText(/rows/)).toBeVisible();
  await expect(page.getByLabel("Results").getByRole("cell", { name: "PO-2026-0002" })).toBeVisible();
});

test("E2E-04 the Procurement Manager raises a PO over several turns", async ({ page }) => {
  await loginAs(page, USERS.pm);
  await ask(page, "Raise a PO for 50 MS Tube 25x40 from Summit Engineering at 120 each");

  await expect(page.getByText(/Which payment terms apply/).first()).toBeVisible();
  await page.getByRole("button", { name: "30 Days Credit" }).first().click();

  const card = page.getByLabel("Purchase order draft");
  await expect(card).toBeVisible();
  await expect(card.getByText(/6,?000\.00/).first()).toBeVisible();
  await card.getByRole("button", { name: "Confirm" }).click();

  await expect(page.getByLabel("Conversation").getByText(/PO-2026-0011/).first()).toBeVisible();
  expect(sql("select count(*) from proc_purchase_orders where po_number = 'PO-2026-0011'")).toBe("1");
  expect(sql("select count(*) from proc_po_payment_tranches t join proc_purchase_orders p " +
             "on p.id = t.po_id where p.po_number = 'PO-2026-0011'")).toBe("1");
});

test("E2E-05 the Warehouse Manager can't raise a PO", async ({ page }) => {
  await loginAs(page, USERS.wm);
  await ask(page, "Raise a PO for 10 relays from Anand Engineering");
  await expect(page.getByText(/Only the Procurement Manager can raise purchase orders/)).toBeVisible();
  expect(sql("select count(*) from assistant.po_drafts d join assistant.conversations c " +
             "on c.id = d.conversation_id where c.user_id = '0b0f6f43-6b63-4c43-9a51-6d1d3b6f0a03'")).toBe("0");
});

test("E2E-06 a refresh restores the conversation and the open PO draft", async ({ page }) => {
  await loginAs(page, USERS.pm);
  await ask(page, "Raise a PO for 20 Hinge Set from Summit Engineering at 1100 each");
  await expect(page.getByText(/Which payment terms apply/).first()).toBeVisible();
  await expect(page).toHaveURL(/[?&]c=/);

  await page.reload();
  await expect(page.getByLabel("Conversation").getByText(/Raise a PO for 20 Hinge Set/)).toBeVisible();
  await expect(page.getByLabel("Purchase order draft")).toBeVisible();
});

test("E2E-07 logging out closes the chat", async ({ page }) => {
  await loginAs(page, USERS.bo);
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/chat");
  await expect(page).toHaveURL(/\/login/);
});
