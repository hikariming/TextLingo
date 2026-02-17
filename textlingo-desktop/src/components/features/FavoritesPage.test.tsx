import { render, screen } from "@testing-library/react";
import { vi, beforeEach, describe, expect, it } from "vitest";
import { FavoritesPage } from "./FavoritesPage";

const invokeMock = vi.fn();

vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  save: vi.fn(),
}));

describe("FavoritesPage", () => {
  beforeEach(() => {
    invokeMock.mockReset();
  });

  it("renders vocabulary list grouped with packs", async () => {
    invokeMock.mockImplementation((command: string) => {
      if (command === "list_favorite_vocabularies_cmd") {
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
      if (command === "list_favorite_grammars_cmd") {
        return Promise.resolve([]);
      }
      if (command === "list_word_packs_cmd") {
        return Promise.resolve([
          { id: "system-ungrouped", name: "未分组", is_system: true },
          { id: "p1", name: "TOEFL", is_system: false },
        ]);
      }
      return Promise.resolve(null);
    });

    render(<FavoritesPage onBack={() => {}} onSelectArticle={() => {}} />);

    await screen.findByText("abandon");
    expect(screen.getByText("TOEFL")).toBeInTheDocument();
    expect(screen.getByText("单词合集")).toBeInTheDocument();
  });
});
