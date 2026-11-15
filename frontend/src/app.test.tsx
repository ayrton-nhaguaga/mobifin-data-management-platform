import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { App, State } from "./main";
import { api, errorText } from "./api";

describe("Interface e autenticação", () => {
  it("redirecciona uma página protegida para o login", () => {
    window.history.replaceState({}, "", "/clients");
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "Aceder à plataforma" }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
  });
  it("submete credenciais para a API e apresenta o erro", async () => {
    const call = vi
      .spyOn(api, "post")
      .mockRejectedValueOnce(new Error("Credenciais inválidas"));
    render(<App />);
    fireEvent.change(screen.getByLabelText("Utilizador"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Palavra-passe"), {
      target: { value: "incorrecta" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Iniciar sessão/ }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Credenciais inválidas",
      ),
    );
    expect(call).toHaveBeenCalledWith(
      "/auth/token",
      expect.any(URLSearchParams),
    );
    call.mockRestore();
  });
  it("apresenta estados de carregamento e erro", () => {
    const view = render(
      <State loading={true} error={null}>
        Conteúdo
      </State>,
    );
    expect(screen.getByText(/A carregar dados/)).toBeInTheDocument();
    view.rerender(
      <State loading={false} error={new Error("Falha da API")}>
        Conteúdo
      </State>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Falha da API");
    view.rerender(
      <State loading={false} error={null}>
        Conteúdo
      </State>,
    );
    expect(screen.getByText("Conteúdo")).toBeInTheDocument();
  });
  it("normaliza erros de comunicação", () => {
    expect(errorText(new Error("Ligação falhou"))).toBe("Ligação falhou");
  });
  it("autentica, apresenta dashboard da API e navega para clientes", async () => {
    window.history.replaceState({}, "", "/login");
    const post = vi
      .spyOn(api, "post")
      .mockResolvedValue({
        data: {
          access_token: "test-token",
          user: {
            id: 1,
            username: "admin",
            full_name: "Administrador",
            role: "ADMIN",
          },
        },
      });
    const get = vi
      .spyOn(api, "get")
      .mockImplementation(async (url) => ({
        data: String(url).startsWith("/dashboard")
          ? {
              clients: 7,
              transactions: 12,
              facts: 8,
              open_incidents: 2,
              metrics: {},
              daily: [],
              quality_history: [],
              incident_distribution: [],
              last_etl: null,
            }
          : { items: [], total: 0 },
      }));
    render(<App />);
    fireEvent.change(screen.getByLabelText("Utilizador"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText("Palavra-passe"), {
      target: { value: "senha-local" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Iniciar sessão/ }));
    await waitFor(() => expect(screen.getByText("7")).toBeInTheDocument());
    expect(get).toHaveBeenCalledWith("/dashboard");
    fireEvent.click(screen.getByRole("link", { name: "Clientes" }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Novo cliente/ }),
      ).toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(
        screen.getByText("Ainda não existem registos"),
      ).toBeInTheDocument(),
    );
    expect(get).toHaveBeenCalledWith("/clients?q=&offset=0");
    fireEvent.click(screen.getByRole("button", { name: "Terminar sessão" }));
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Aceder à plataforma" }),
      ).toBeInTheDocument(),
    );
    post.mockRestore();
    get.mockRestore();
  });
});
