import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, beforeEach, describe, expect, it } from "vitest";
import { WordRecitePanel } from "./WordRecitePanel";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

describe("WordRecitePanel", () => {
  beforeEach(() => {
    invokeMock.mockReset();
  });

  it("loads due queue and submits review grade", async () => {
    invokeMock.mockImplementation((command: string) => {
      if (command === "get_due_vocabulary_queue_cmd") {
        return Promise.resolve([
          {
            id: "v1",
            word: "abandon",
            meaning: "放弃",
            usage: "v.",
            pack_ids: ["p1"],
            srs_state: "new",
            due_date: "2026-02-16",
            review_count: 0,
            created_at: "2026-02-16T00:00:00Z",
          },
        ]);
      }
      if (command === "review_vocabulary_cmd") {
        return Promise.resolve({});
      }
      return Promise.resolve(null);
    });

    const onReviewed = vi.fn(async () => {});

    render(
      <WordRecitePanel
        open
        onOpenChange={() => {}}
        packId="p1"
        packName="TOEFL"
        onReviewed={onReviewed}
      />
    );

    await screen.findByText("abandon");
    await userEvent.click(screen.getByRole("button", { name: "显示答案" }));
    await userEvent.click(screen.getByRole("button", { name: "认识" }));

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledWith(
        "review_vocabulary_cmd",
        expect.objectContaining({ vocabularyId: "v1", grade: "known" })
      );
      expect(onReviewed).toHaveBeenCalled();
    });
  });
});
