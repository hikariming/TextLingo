import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, beforeEach, describe, expect, it } from "vitest";
import { SelectPackDialog } from "./SelectPackDialog";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

describe("SelectPackDialog", () => {
  beforeEach(() => {
    invokeMock.mockReset();
  });

  it("loads packs and confirms selected pack ids", async () => {
    invokeMock.mockImplementation((command: string) => {
      if (command === "list_word_packs_cmd") {
        return Promise.resolve([
          { id: "p1", name: "未分组", is_system: true },
          { id: "p2", name: "TOEFL", is_system: false },
        ]);
      }
      return Promise.resolve(null);
    });

    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();

    render(
      <SelectPackDialog
        open
        onOpenChange={onOpenChange}
        onConfirm={onConfirm}
        initialSelectedPackIds={["p1"]}
      />
    );

    await screen.findByText("TOEFL");

    await userEvent.click(screen.getByLabelText("TOEFL"));
    await userEvent.click(screen.getByRole("button", { name: "确认" }));

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledTimes(1);
      const selected = onConfirm.mock.calls[0][0] as string[];
      expect(selected).toContain("p1");
      expect(selected).toContain("p2");
    });
  });
});
