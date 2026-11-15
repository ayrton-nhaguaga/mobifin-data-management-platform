import axios from "axios";
export const api = axios.create({ baseURL: "/api", timeout: 300000 });
let bearer = "";
export function setToken(value: string) {
  bearer = value;
}
api.interceptors.request.use((config) => {
  if (bearer) config.headers.Authorization = `Bearer ${bearer}`;
  return config;
});
export function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((x) => `${x.loc?.slice(1).join(".")}: ${x.msg}`).join("; ")
        : "Não foi possível comunicar com a API.";
  }
  return error instanceof Error ? error.message : "Erro inesperado";
}
