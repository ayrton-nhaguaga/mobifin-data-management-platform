import React, {
  createContext,
  useContext,
  useState,
  FormEvent,
  ReactNode,
} from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  NavLink,
  useLocation,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { ReactFlow, Background, Controls, MarkerType } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  BarChart,
  Bar,
} from "recharts";
import {
  LayoutDashboard,
  Users,
  ArrowLeftRight,
  UploadCloud,
  ShieldCheck,
  Database,
  ScanLine,
  GitBranch,
  Workflow,
  TriangleAlert,
  ScrollText,
  ChartNoAxesCombined,
  UserCog,
  LogOut,
  ChevronRight,
  Plus,
  Search,
  X,
  RefreshCw,
  Check,
  Menu,
  KeyRound,
  ArrowUpRight,
  Activity,
  CircleDot,
  FileCheck2,
} from "lucide-react";
import { api, setToken, errorText } from "./api";
import "./styles.css";

type Row = Record<string, any>;
type Person = { id: number; username: string; full_name: string; role: string };
type AuthState = {
  user: Person | null;
  login: (token: string, user: Person) => void;
  logout: () => void;
};
const Auth = createContext<AuthState>({
  user: null,
  login: () => {},
  logout: () => {},
});
const labels: Record<string, string> = {
  completeness: "Completude",
  uniqueness: "Unicidade",
  validity: "Validade",
  timeliness: "Actualidade",
  consistency: "Consistência",
};
const nav = [
  ["/", "Visão geral", LayoutDashboard],
  ["/clients", "Clientes", Users],
  ["/transactions", "Transacções", ArrowLeftRight],
  ["/imports", "Importação de dados", UploadCloud],
  ["/governance", "Data Governance", ShieldCheck],
  ["/catalog", "Catálogo de metadados", Database],
  ["/quality", "Data Quality", ScanLine],
  ["/validations", "Validações", FileCheck2],
  ["/lineage", "Data Lineage", GitBranch],
  ["/etl", "Processos ETL", Workflow],
  ["/incidents", "Incidentes", TriangleAlert],
  ["/audit", "Auditoria", ScrollText],
  ["/reports", "Relatórios", ChartNoAxesCombined],
  ["/users", "Utilizadores", UserCog],
] as const;
const fmt = (v: any) =>
  v === null || v === undefined
    ? "—"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v);
const number = (v: number) => new Intl.NumberFormat("pt-MZ").format(v);
const date = (v: any) =>
  v ? new Date(v).toLocaleString("pt-MZ", { timeZone: "Africa/Maputo" }) : "—";
function useData(key: string, endpoint = key) {
  return useQuery<Row>({
    queryKey: [key],
    queryFn: async () => (await api.get(endpoint)).data,
  });
}
function Badge({ value }: { value: any }) {
  return (
    <span
      className={`badge ${["SUCCESS", "COMPLETED", "RESOLVED", "CLOSED", "PROCESSED", true].includes(value) ? "good" : ["OPEN", "HIGH", "FAILURE", false].includes(value) ? "bad" : ""}`}
    >
      {fmt(value)}
    </span>
  );
}
export function State({
  loading,
  error,
  children,
}: {
  loading: boolean;
  error: unknown;
  children: ReactNode;
}) {
  return loading ? (
    <div className="state">
      <RefreshCw className="spin" size={22} /> A carregar dados…
    </div>
  ) : error ? (
    <div className="error" role="alert">
      {errorText(error)}
    </div>
  ) : (
    <>{children}</>
  );
}
function Empty() {
  return (
    <div className="state">
      <Database size={26} />
      <strong>Ainda não existem registos</strong>
      <span>Importe um ficheiro ou crie o primeiro registo para começar.</span>
    </div>
  );
}
function Table({
  rows,
  columns,
  action,
}: {
  rows: Row[];
  columns: [string, string][];
  action?: (row: Row) => ReactNode;
}) {
  return rows.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map(([key, label]) => (
              <th key={key}>{label}</th>
            ))}
            {action && <th>Acções</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id ?? i}>
              {columns.map(([key]) => (
                <td key={key}>
                  {key.includes("status") ||
                  key === "role" ||
                  key === "classification" ? (
                    <Badge value={row[key]} />
                  ) : key.endsWith("_at") ? (
                    date(row[key])
                  ) : (
                    fmt(row[key])
                  )}
                </td>
              ))}
              {action && (
                <td>
                  <div className="actions">{action(row)}</div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty />
  );
}
function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="modal-shade"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon" onClick={onClose} aria-label="Fechar">
            <X />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
type Field = {
  key: string;
  label: string;
  type?: string;
  options?: string[];
  optional?: boolean;
  default?: any;
};
function Editor({
  title,
  fields,
  initial = {},
  onClose,
  save,
}: {
  title: string;
  fields: Field[];
  initial?: Row;
  onClose: () => void;
  save: (data: Row) => Promise<any>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(e.currentTarget);
    const data: Row = {};
    for (const f of fields) {
      const value = String(form.get(f.key) ?? "");
      data[f.key] =
        f.type === "number"
          ? Number(value)
          : f.type === "boolean"
            ? value === "true"
            : f.type === "json"
              ? value
              : value || null;
    }
    try {
      for (const f of fields.filter((f) => f.type === "json"))
        data[f.key] = JSON.parse(data[f.key]);
      await save(data);
      onClose();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="form-grid">
          {fields.map((f) => (
            <label
              key={f.key}
              className={
                f.type === "textarea" || f.type === "json" ? "wide" : ""
              }
            >
              {f.label}
              {f.type === "textarea" || f.type === "json" ? (
                <textarea
                  name={f.key}
                  required={!f.optional}
                  defaultValue={
                    f.type === "json"
                      ? JSON.stringify(
                          initial[f.key] ?? f.default ?? {},
                          null,
                          2,
                        )
                      : (initial[f.key] ?? f.default ?? "")
                  }
                  rows={f.type === "json" ? 9 : 4}
                />
              ) : f.options || f.type === "boolean" ? (
                <select
                  name={f.key}
                  defaultValue={String(
                    initial[f.key] ?? f.default ?? f.options?.[0] ?? true,
                  )}
                >
                  {(f.options ?? ["true", "false"]).map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              ) : (
                <input
                  name={f.key}
                  type={f.type ?? "text"}
                  required={!f.optional}
                  min={f.type === "number" ? 0 : undefined}
                  step={f.type === "number" ? "any" : undefined}
                  defaultValue={
                    f.type === "datetime-local" && initial[f.key]
                      ? new Date(
                          new Date(initial[f.key]).getTime() -
                            new Date(initial[f.key]).getTimezoneOffset() *
                              60000,
                        )
                          .toISOString()
                          .slice(0, 16)
                      : (initial[f.key] ?? f.default ?? "")
                  }
                />
              )}
            </label>
          ))}
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <footer>
          <button type="button" className="secondary" onClick={onClose}>
            Cancelar
          </button>
          <button disabled={busy}>
            {busy ? "A guardar…" : "Guardar alterações"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
export function Login() {
  const auth = useContext(Auth);
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const form = new FormData(e.currentTarget);
      const res = await api.post(
        "/auth/token",
        new URLSearchParams({
          username: String(form.get("username")),
          password: String(form.get("password")),
        }),
      );
      auth.login(res.data.access_token, res.data.user);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <div className="login-story">
        <div className="brand">
          <span className="brand-icon">
            <Activity />
          </span>
          MobiFin<span className="brand-dot">.</span>
        </div>
        <div>
          <span className="eyebrow">DATA MANAGEMENT PLATFORM</span>
          <h1>
            Confiança nos dados.
            <br />
            Clareza nas decisões.
          </h1>
          <p>
            Governação, qualidade e rastreabilidade dos dados financeiros num
            único lugar.
          </p>
          <div className="story-line">
            <ShieldCheck /> Governar <ChevronRight />
            <ScanLine /> Validar <ChevronRight />
            <GitBranch /> Rastrear
          </div>
        </div>
        <small>ISUTC · Engenharia de Dados · Demonstração académica</small>
      </div>
      <div className="login-panel">
        <form onSubmit={submit}>
          <span className="eyebrow">BEM-VINDO À MOBIFIN</span>
          <h2>Aceder à plataforma</h2>
          <p>Introduza as credenciais da sua conta.</p>
          <label>
            Utilizador
            <input
              name="username"
              autoComplete="username"
              required
              placeholder="O seu utilizador"
            />
          </label>
          <label>
            Palavra-passe
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              placeholder="A sua palavra-passe"
            />
          </label>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          <button disabled={busy}>
            {busy ? "A autenticar…" : "Iniciar sessão"}
            <ArrowUpRight size={18} />
          </button>
          <small>
            Ambiente académico · Dados exclusivamente sintéticos
            <br />
            Credenciais configuradas no ficheiro .env local.
          </small>
        </form>
      </div>
    </div>
  );
}
function Dashboard() {
  const { data: d, isPending, error } = useData("/dashboard");
  const [currency, setCurrency] = useState("MZN");
  const metrics = d?.metrics ?? {};
  const history = (d?.quality_history ?? []).map((r: Row) => ({
    name: `#${r.id}`,
    ...Object.fromEntries(
      Object.keys(labels).map((k) => [k, r.metrics[k]?.percentage]),
    ),
  }));
  return (
    <State loading={isPending} error={error}>
      <div className="welcome">
        <div>
          <span className="eyebrow">INTELIGÊNCIA E CONTROLO DOS DADOS</span>
          <h2>Os seus dados, em perspectiva.</h2>
          <p>Acompanhe a saúde dos dados e a actividade da plataforma.</p>
        </div>
        <div className="live">
          <span />
          Dados da API · Actualização ao abrir
        </div>
      </div>
      <div className="stats">
        <Stat
          label="Clientes registados"
          value={number(d?.clients ?? 0)}
          icon={<Users />}
        />
        <Stat
          label="Transacções operacionais"
          value={number(d?.transactions ?? 0)}
          icon={<ArrowLeftRight />}
        />
        <Stat
          label="Incidentes em aberto"
          value={number(d?.open_incidents ?? 0)}
          icon={<TriangleAlert />}
        />
        <Stat
          label="Factos no warehouse"
          value={number(d?.facts ?? 0)}
          icon={<Database />}
        />
      </div>
      <section className="panel quality-panel">
        <div className="section-title">
          <div>
            <h3>Qualidade dos dados</h3>
            <p>Última validação de cada lote · metas académicas</p>
          </div>
          <NavLink to="/quality">
            Ver regras <ChevronRight size={15} />
          </NavLink>
        </div>
        <div className="quality-grid">
          {Object.entries(labels).map(([key, label]) => {
            const m = metrics[key];
            const pct = m?.percentage;
            return (
              <div className="quality-item" key={key}>
                <span>{label}</span>
                <strong>
                  {pct == null
                    ? "—"
                    : `${Number(pct).toLocaleString("pt-MZ", { maximumFractionDigits: 2 })}%`}
                </strong>
                <div className="progress">
                  <i
                    style={{
                      width: `${pct ?? 0}%`,
                      background: pct >= m?.target ? "#278579" : "#cf9850",
                    }}
                  />
                </div>
                <small>
                  Meta ≥ {m?.target ?? "—"}% · n = {m?.denominator ?? 0}
                </small>
              </div>
            );
          })}
        </div>
        <p className="footnote">
          Sem universo avaliado, o indicador fica indisponível. Consistência:{" "}
          {metrics.consistency?.unexplained_differences ?? 0} diferenças sem
          justificação; {metrics.consistency?.reconciliations ?? 0}{" "}
          reconciliações.
        </p>
      </section>
      <div className="chart-grid">
        <section className="panel">
          <div className="section-title">
            <div>
              <h3>Evolução da qualidade</h3>
              <p>Resultados observados por execução</p>
            </div>
            <Activity size={20} />
          </div>
          {history.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={history}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                {["completeness", "uniqueness", "validity"].map((k, i) => (
                  <Area
                    key={k}
                    type="monotone"
                    name={labels[k]}
                    dataKey={k}
                    stroke={["#244f82", "#299184", "#c79b55"][i]}
                    fill={["#244f8210", "#29918410", "#c79b5510"][i]}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <Empty />
          )}
        </section>
        <section className="panel">
          <div className="section-title">
            <div>
              <h3>Incidentes por estado</h3>
              <p>Distribuição actual</p>
            </div>
            <CircleDot size={20} />
          </div>
          {d?.incident_distribution.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={d.incident_distribution}
                  dataKey="count"
                  nameKey="status"
                  innerRadius={65}
                  outerRadius={90}
                >
                  {d.incident_distribution.map((_: Row, i: number) => (
                    <Cell
                      key={i}
                      fill={
                        [
                          "#244f82",
                          "#d1a15b",
                          "#299184",
                          "#8c9bb0",
                          "#b86a6a",
                          "#6f8fb7",
                        ][i % 6]
                      }
                    />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <Empty />
          )}
        </section>
      </div>
      <section className="panel">
        <div className="section-title">
          <div>
            <h3>Volume financeiro diário</h3>
            <p>Apenas transacções elegíveis consolidadas</p>
          </div>
          <select
            aria-label="Moeda"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          >
            {["MZN", "USD", "ZAR", "EUR"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </div>
        {d?.daily.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={d.daily
                .filter((r: Row) => r.currency === currency)
                .map((r: Row) => ({ ...r, volume: Number(r.volume) }))}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Bar
                dataKey="volume"
                name={`Volume (${currency})`}
                fill="#2b547e"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <Empty />
        )}
        <div className="etl-note">
          <Workflow size={17} /> Última execução ETL:{" "}
          {d?.last_etl
            ? `#${d.last_etl.id} · ${date(d.last_etl.finished_at)} · ${d.last_etl.loaded} linhas carregadas`
            : "Nenhuma execução registada"}
        </div>
      </section>
    </State>
  );
}
function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: ReactNode;
}) {
  return (
    <article className="stat">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="stat-icon">{icon}</div>
    </article>
  );
}

const clientFields: Field[] = [
  { key: "external_id", label: "Identificador externo" },
  { key: "name", label: "Nome completo" },
  { key: "document", label: "Documento" },
  { key: "phone", label: "Telefone" },
  { key: "email", label: "Email", type: "email", optional: true },
  { key: "birth_date", label: "Nascimento", type: "date", optional: true },
  { key: "address", label: "Endereço", optional: true, default: "" },
  { key: "source", label: "Fonte", default: "MANUAL" },
];
const txFields: Field[] = [
  { key: "external_id", label: "ID externo" },
  { key: "client_id", label: "ID interno do cliente", type: "number" },
  {
    key: "operation",
    label: "Operação",
    options: ["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"],
  },
  { key: "amount", label: "Montante (decimal)", default: "100.00" },
  { key: "currency", label: "Moeda", options: ["MZN", "USD", "ZAR", "EUR"] },
  { key: "occurred_at", label: "Data e hora", type: "datetime-local" },
  {
    key: "status",
    label: "Estado",
    options: ["COMPLETED", "PENDING", "CANCELLED"],
  },
  { key: "source", label: "Fonte", default: "MANUAL" },
  { key: "external_ref", label: "Referência externa" },
];
function Operational({ kind }: { kind: "clients" | "transactions" }) {
  const [search, setSearch] = useState(""),
    [offset, setOffset] = useState(0),
    [edit, setEdit] = useState<Row | null>(null);
  const endpoint = `/${kind}?q=${encodeURIComponent(search)}&offset=${offset}`;
  const query = useData(endpoint);
  const qc = useQueryClient();
  const user = useContext(Auth).user!;
  const can = ["ADMIN", "DATA_STEWARD", "DATA_ENGINEER"].includes(user.role);
  const columns: [string, string][] =
    kind === "clients"
      ? [
          ["id", "ID"],
          ["external_id", "Referência"],
          ["name", "Nome completo"],
          ["document", "Documento"],
          ["phone", "Telefone"],
          ["email", "Email"],
          ["source", "Fonte"],
        ]
      : [
          ["id", "ID"],
          ["external_id", "Referência"],
          ["client_id", "Cliente"],
          ["operation", "Operação"],
          ["amount", "Montante"],
          ["currency", "Moeda"],
          ["status", "Estado"],
          ["occurred_at", "Data"],
        ];
  return (
    <>
      <div className="toolbar">
        <div className="search">
          <Search size={17} />
          <input
            aria-label="Pesquisar"
            placeholder="Pesquisar por nome ou referência…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </div>
        {can && (
          <button onClick={() => setEdit({})}>
            <Plus size={17} />
            Novo {kind === "clients" ? "cliente" : "registo"}
          </button>
        )}
      </div>
      <section className="panel flush">
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={columns}
            action={
              can
                ? (row) => (
                    <button className="text-btn" onClick={() => setEdit(row)}>
                      Editar
                    </button>
                  )
                : undefined
            }
          />
          <Pagination
            offset={offset}
            total={query.data?.total ?? 0}
            setOffset={setOffset}
          />
        </State>
      </section>
      {edit && (
        <Editor
          title={`${edit.id ? "Editar" : "Criar"} ${kind === "clients" ? "cliente" : "transacção"}`}
          fields={kind === "clients" ? clientFields : txFields}
          initial={edit}
          onClose={() => setEdit(null)}
          save={async (data) => {
            if (kind === "clients") {
              data.address ??= "";
            } else {
              data.occurred_at = new Date(data.occurred_at).toISOString();
            }
            await (edit.id
              ? api.put(`/${kind}/${edit.id}`, data)
              : api.post(`/${kind}`, data));
            await qc.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
function Pagination({
  offset,
  total,
  setOffset,
}: {
  offset: number;
  total: number;
  setOffset: (n: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {total ? offset + 1 : 0}–{Math.min(offset + 50, total)} de{" "}
        {number(total)} registos
      </span>
      <div>
        <button
          className="secondary"
          disabled={!offset}
          onClick={() => setOffset(Math.max(0, offset - 50))}
        >
          Anterior
        </button>
        <button
          className="secondary"
          disabled={offset + 50 >= total}
          onClick={() => setOffset(offset + 50)}
        >
          Seguinte
        </button>
      </div>
    </div>
  );
}
function Imports() {
  const [dataset, setDataset] = useState("clients"),
    [file, setFile] = useState<File | null>(null),
    [batch, setBatch] = useState<Row | null>(null),
    [correction, setCorrection] = useState<Row | null>(null);
  const query = useData("/batches");
  const qc = useQueryClient();
  const user = useContext(Auth).user!;
  const can = ["ADMIN", "DATA_ENGINEER"].includes(user.role);
  const raw = ["ADMIN", "DATA_ENGINEER", "DATA_STEWARD"].includes(user.role);
  const stage = useQuery<Row>({
    queryKey: ["stage", batch?.id],
    queryFn: async () => (await api.get(`/batches/${batch?.id}/rows`)).data,
    enabled: !!batch && raw,
  });
  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Seleccione um ficheiro CSV");
      const form = new FormData();
      form.append("file", file);
      return api.post(`/imports/${dataset}`, form);
    },
    onSuccess: () => {
      qc.invalidateQueries();
      setFile(null);
    },
  });
  return (
    <>
      {can && (
        <section className="panel">
          <div className="section-title">
            <div>
              <h3>Uma entrada controlada para os seus dados</h3>
              <p>
                Os ficheiros ficam em staging. A importação preserva os erros
                para análise.
              </p>
            </div>
            <UploadCloud />
          </div>
          <div className="upload-box">
            <UploadCloud size={32} />
            <strong>Importar ficheiro CSV</strong>
            <span>UTF-8 · até 10 MiB · até 50 000 linhas</span>
            <select
              aria-label="Dataset"
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
            >
              <option value="clients">Clientes</option>
              <option value="transactions">Transacções</option>
            </select>
            <input
              aria-label="Ficheiro CSV"
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <button
              disabled={mutation.isPending || !file}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? "A importar…" : "Importar para staging"}
            </button>
          </div>
          {mutation.error && (
            <div className="error">{errorText(mutation.error)}</div>
          )}
          {mutation.isSuccess && (
            <p className="success">
              Lote registado. Execute a validação na página Data Quality.
            </p>
          )}
        </section>
      )}
      <section className="panel flush">
        <div className="section-title padded">
          <h3>Lotes de importação</h3>
        </div>
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "Lote"],
              ["filename", "Ficheiro"],
              ["dataset", "Dataset"],
              ["row_count", "Linhas"],
              ["revision", "Revisão"],
              ["status", "Estado"],
              ["created_at", "Importado em"],
            ]}
            action={
              raw
                ? (row) => (
                    <button className="text-btn" onClick={() => setBatch(row)}>
                      Staging
                    </button>
                  )
                : undefined
            }
          />
        </State>
      </section>
      {batch && (
        <Modal
          title={`Staging · lote #${batch.id}`}
          onClose={() => setBatch(null)}
        >
          <p>
            Primeiras 50 linhas. O ID da linha permite correcção e consulta de
            incidentes. O original é preservado.
          </p>
          <State loading={stage.isPending} error={stage.error}>
            <Table
              rows={(stage.data?.items ?? []).map((r: Row) => ({
                ...r,
                preview: JSON.stringify(r.data),
              }))}
              columns={[
                ["id", "ID da linha"],
                ["row_number", "Linha CSV"],
                ["preview", "Dados actuais"],
                ["loaded", "Carregado"],
              ]}
              action={
                ["ADMIN", "DATA_STEWARD"].includes(user.role)
                  ? (row) => (
                      <button
                        className="text-btn"
                        disabled={row.loaded}
                        onClick={() => setCorrection(row)}
                      >
                        Corrigir
                      </button>
                    )
                  : undefined
              }
            />
          </State>
        </Modal>
      )}
      {correction && (
        <Editor
          title={`Corrigir linha #${correction.id}`}
          initial={correction}
          fields={[
            { key: "data", label: "Campos e valores (JSON)", type: "json" },
            { key: "reason", label: "Justificação", type: "textarea" },
          ]}
          onClose={() => setCorrection(null)}
          save={async (data) => {
            await api.patch(`/staging/${correction.id}`, data);
            await qc.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
function Quality() {
  const query = useData("/rules");
  const batches = useData("/batches");
  const qc = useQueryClient();
  const [selected, setSelected] = useState(""),
    [create, setCreate] = useState(false);
  const user = useContext(Auth).user!;
  const manage = ["ADMIN", "DATA_STEWARD"].includes(user.role);
  const run = useMutation({
    mutationFn: () => api.post("/validations", { batch_id: Number(selected) }),
    onSuccess: () => qc.invalidateQueries(),
  });
  const toggle = useMutation({
    mutationFn: (r: Row) => api.patch(`/rules/${r.id}`, { active: !r.active }),
    onSuccess: () => qc.invalidateQueries(),
  });
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <div>
            <h3>Motor de qualidade</h3>
            <p>
              Regras persistidas, resultados reproduzíveis e incidentes
              automáticos.
            </p>
          </div>
          <ScanLine />
        </div>
        <div className="inline-form">
          <select
            aria-label="Lote a validar"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Seleccione um lote…</option>
            {batches.data?.items.map((b: Row) => (
              <option value={b.id} key={b.id}>
                #{b.id} · {b.filename} · rev. {b.revision}
              </option>
            ))}
          </select>
          <button
            disabled={
              !selected ||
              run.isPending ||
              !["ADMIN", "DATA_STEWARD", "DATA_ENGINEER"].includes(user.role)
            }
            onClick={() => run.mutate()}
          >
            <RefreshCw size={16} />
            {run.isPending ? "A validar…" : "Executar validação"}
          </button>
        </div>
        {run.error && <div className="error">{errorText(run.error)}</div>}
        {run.isSuccess && (
          <p className="success">
            Validação persistida. Consulte os resultados e incidentes.
          </p>
        )}
        <p className="footnote">
          Metas: completude ≥ 98%; unicidade ≥ 99%; validade ≥ 99,5%; relatórios
          D+1 ≥ 99%; diferenças justificadas = 100%. As invariantes operacionais
          aplicam-se mesmo com regras desactivadas.
        </p>
      </section>
      <section className="panel flush">
        <div className="section-title padded">
          <h3>Regras de validação</h3>
          {manage && (
            <button onClick={() => setCreate(true)}>
              <Plus size={16} />
              Nova regra
            </button>
          )}
        </div>
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "ID"],
              ["name", "Regra"],
              ["dataset", "Dataset"],
              ["dimension", "Dimensão"],
              ["field", "Campo"],
              ["target", "Meta %"],
              ["active", "Activa"],
            ]}
            action={
              manage
                ? (r) => (
                    <button
                      className="text-btn"
                      onClick={() => toggle.mutate(r)}
                      disabled={toggle.isPending}
                    >
                      {r.active ? "Desactivar" : "Activar"}
                    </button>
                  )
                : undefined
            }
          />
        </State>
        {toggle.error && <div className="error">{errorText(toggle.error)}</div>}
      </section>
      {create && (
        <Editor
          title="Criar regra"
          fields={[
            {
              key: "dataset",
              label: "Dataset",
              options: ["clients", "transactions"],
            },
            { key: "name", label: "Nome" },
            {
              key: "dimension",
              label: "Dimensão",
              options: ["completeness", "uniqueness", "validity"],
            },
            {
              key: "kind",
              label: "Tipo",
              options: [
                "required",
                "unique",
                "email",
                "positive",
                "date",
                "operation",
                "reference",
                "currency",
                "phone",
              ],
            },
            { key: "field", label: "Campo" },
            { key: "target", label: "Meta %", type: "number", default: 99 },
            { key: "active", label: "Activa", type: "boolean" },
            { key: "blocking", label: "Bloqueante", type: "boolean" },
          ]}
          onClose={() => setCreate(false)}
          save={async (data) => {
            await api.post("/rules", data);
            await qc.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
function Validations() {
  const query = useData("/validations");
  const [selected, setSelected] = useState<Row | null>(null),
    [comparison, setComparison] = useState<Row | null>(null),
    [dimension, setDimension] = useState("");
  const violations = useQuery<Row>({
    queryKey: ["violations", selected?.id, dimension],
    queryFn: async () =>
      (
        await api.get(
          `/violations?run_id=${selected?.id}&dimension=${dimension}`,
        )
      ).data,
    enabled: !!selected,
  });
  return (
    <>
      <section className="panel flush">
        <div className="section-title padded">
          <div>
            <h3>Histórico de validações</h3>
            <p>
              Seleccione duas execuções para comparar indicadores e
              denominadores.
            </p>
          </div>
        </div>
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "Execução"],
              ["batch_id", "Lote"],
              ["revision", "Revisão"],
              ["evaluated", "Avaliados"],
              ["rejected", "Rejeitados"],
              ["created_at", "Data"],
            ]}
            action={(r) => (
              <>
                <button className="text-btn" onClick={() => setSelected(r)}>
                  Resultados
                </button>
                <button className="text-btn" onClick={() => setComparison(r)}>
                  Comparar
                </button>
              </>
            )}
          />
        </State>
      </section>
      {selected && (
        <section className="panel">
          <div className="section-title">
            <h3>
              Execução #{selected.id}
              {comparison ? ` vs #${comparison.id}` : ""}
            </h3>
            {comparison && (
              <button className="text-btn" onClick={() => setComparison(null)}>
                Limpar comparação
              </button>
            )}
          </div>
          <Table
            rows={Object.entries(selected.metrics).map(([k, v]) => ({
              dimension: labels[k],
              ...(v as Row),
              previous: comparison?.metrics[k]?.percentage ?? "—",
            }))}
            columns={[
              ["dimension", "Dimensão"],
              ["passed", "Conformes"],
              ["denominator", "Denominador"],
              ["unit", "Unidade"],
              ["percentage", "Resultado %"],
              ["target", "Meta %"],
              ["previous", "Comparação %"],
            ]}
          />
          <div className="section-title">
            <h3>Violações · primeiras 50</h3>
            <select
              aria-label="Dimensão"
              value={dimension}
              onChange={(e) => setDimension(e.target.value)}
            >
              <option value="">Todas as dimensões</option>
              {Object.entries(labels)
                .slice(0, 3)
                .map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
            </select>
          </div>
          <State loading={violations.isPending} error={violations.error}>
            <Table
              rows={violations.data?.items ?? []}
              columns={[
                ["id", "ID"],
                ["row_id", "Linha staging"],
                ["rule_id", "Regra"],
                ["dimension", "Dimensão"],
                ["message", "Descrição"],
              ]}
            />
          </State>
        </section>
      )}
    </>
  );
}
function ETL() {
  const query = useData("/etl"),
    batches = useData("/batches");
  const [selected, setSelected] = useState(""),
    [detail, setDetail] = useState<Row | null>(null),
    [justification, setJustification] = useState<Row | null>(null);
  const qc = useQueryClient(),
    user = useContext(Auth).user!;
  const reconcile = useMutation({
    mutationFn: (id: number) => api.post(`/etl/${id}/reconcile`),
    onSuccess: (r) => {
      setDetail(r.data);
      qc.invalidateQueries();
    },
  });
  const run = useMutation({
    mutationFn: () => api.post("/etl", { batch_id: Number(selected) }),
    onSuccess: () => qc.invalidateQueries(),
  });
  const retry = useMutation({
    mutationFn: () => api.post("/etl/retry", { batch_id: Number(selected) }),
    onSuccess: () => qc.invalidateQueries(),
  });
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <div>
            <h3>Pipeline de processamento</h3>
            <p>
              Validação → transformação Pandas → operacional → modelo
              dimensional → reconciliação
            </p>
          </div>
          <Workflow />
        </div>
        <div className="inline-form">
          <select
            aria-label="Lote ETL"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Seleccione o lote…</option>
            {batches.data?.items.map((r: Row) => (
              <option key={r.id} value={r.id}>
                #{r.id} · {r.filename}
              </option>
            ))}
          </select>
          <button
            disabled={
              !selected ||
              run.isPending ||
              !["ADMIN", "DATA_ENGINEER"].includes(user.role)
            }
            onClick={() => {
              if (
                window.confirm(
                  "Executar validação e carregar as linhas elegíveis deste lote?",
                )
              )
                run.mutate();
            }}
          >
            {run.isPending ? "A processar…" : "Executar ETL"}
          </button>
          <button className="secondary" disabled={!selected || retry.isPending || run.isPending || !["ADMIN", "DATA_ENGINEER"].includes(user.role)} onClick={() => {
            if (window.confirm("Criar nova revisão e tentar apenas as linhas ainda não carregadas?")) retry.mutate();
          }}>{retry.isPending ? "A reprocessar…" : "Reprocessar rejeitados"}</button>
        </div>
        <p className="footnote">
          Idempotência por lote/revisão. Clientes devem ser processados antes
          das transacções. Apenas COMPLETED entra na tabela de factos.
        </p>
        {run.error && <div className="error">{errorText(run.error)}</div>}
        {retry.error && <div className="error">{errorText(retry.error)}</div>}
        {retry.isSuccess && <p className="success">Nova tentativa concluída; linhas já carregadas preservadas.</p>}
        {run.isSuccess && (
          <p className="success">
            Execução concluída. Os resultados estão persistidos.
          </p>
        )}
      </section>
      <section className="panel flush">
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "Execução"],
              ["batch_id", "Lote"],
              ["loaded", "Carregados"],
              ["rejected", "Rejeitados"],
              ["status", "Estado"],
              ["finished_at", "Fim"],
              ["on_time", "D+1"],
            ]}
            action={(r) => (
              <>
                <button className="text-btn" onClick={() => setDetail(r)}>
                  Reconciliação
                </button>
                {["ADMIN", "DATA_ENGINEER", "AUDITOR"].includes(user.role) && (
                  <button
                    className="text-btn"
                    disabled={reconcile.isPending}
                    onClick={() => reconcile.mutate(r.id)}
                  >
                    Reconciliar
                  </button>
                )}
              </>
            )}
          />
        </State>
      </section>
      {detail && (
        <Modal
          title={`Reconciliação · ETL #${detail.id}`}
          onClose={() => setDetail(null)}
        >
          <Table
            rows={detail.reconciliation}
            columns={[
              ["currency", "Moeda"],
              ["source", "Origem elegível"],
              ["warehouse", "Warehouse"],
              ["difference", "Diferença"],
              ["justification", "Justificação"],
            ]}
            action={
              ["ADMIN", "DATA_OWNER"].includes(user.role)
                ? (r) =>
                    Number(r.difference) !== 0 ? (
                      <button
                        className="text-btn"
                        onClick={() =>
                          setJustification({
                            run_id: detail.id,
                            currency: r.currency,
                          })
                        }
                      >
                        Justificar
                      </button>
                    ) : null
                : undefined
            }
          />
          <p className="footnote">
            A origem elegível contém apenas transacções conformes COMPLETED
            carregadas nesta execução. Prazo D+1: {date(detail.deadline)}
          </p>
        </Modal>
      )}
      {reconcile.error && <p className="error">{errorText(reconcile.error)}</p>}
      {justification && (
        <Editor
          title="Justificar diferença financeira"
          initial={justification}
          fields={[
            {
              key: "currency",
              label: "Moeda",
              options: [justification.currency],
            },
            {
              key: "reason",
              label: "Justificação e evidência",
              type: "textarea",
            },
          ]}
          onClose={() => setJustification(null)}
          save={async (data) => {
            const response = await api.post(
              `/etl/${justification.run_id}/justify`,
              data,
            );
            setDetail(response.data);
            await qc.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
function Governance() {
  const query = useData("/policies"),
    catalog = useData("/catalog");
  const qc = useQueryClient();
  const [edit, setEdit] = useState<Row | null>(null);
  const can = ["ADMIN", "DATA_OWNER"].includes(useContext(Auth).user!.role);
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <div>
            <h3>Responsabilidade sobre os dados</h3>
            <p>Domínios, papéis e classificações de segurança</p>
          </div>
          <ShieldCheck />
        </div>
        <State loading={catalog.isPending} error={catalog.error}>
          <Table
            rows={catalog.data?.items ?? []}
            columns={[
              ["name", "Domínio"],
              ["owner", "Data Owner"],
              ["steward", "Data Steward"],
              ["engineer", "Engenheiro"],
              ["auditor", "Auditor"],
              ["classification", "Classificação"],
            ]}
          />
        </State>
        <div className="classification-row">
          {["PÚBLICA", "INTERNA", "CONFIDENCIAL", "RESTRITA"].map((x) => (
            <Badge key={x} value={x} />
          ))}
        </div>
      </section>
      <section className="panel flush">
        <div className="section-title padded">
          <h3>Políticas e versões</h3>
          {can && (
            <button onClick={() => setEdit({})}>
              <Plus size={16} />
              Nova política
            </button>
          )}
        </div>
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "ID"],
              ["name", "Política"],
              ["owner", "Responsável"],
              ["version", "Versão"],
              ["active", "Activa"],
              ["updated_at", "Actualização"],
            ]}
            action={
              can
                ? (r) => (
                    <button className="text-btn" onClick={() => setEdit(r)}>
                      Editar / versionar
                    </button>
                  )
                : undefined
            }
          />
        </State>
      </section>
      {query.data?.items.map((r: Row) => (
        <details className="panel" key={r.id}>
          <summary>
            {r.name} · v{r.version}
          </summary>
          <p>{r.content}</p>
          {r.history.map((h: Row) => (
            <p className="footnote" key={h.version}>
              v{h.version} · {h.content}
            </p>
          ))}
        </details>
      ))}
      {edit && (
        <Editor
          title={edit.id ? "Versionar política" : "Criar política"}
          initial={edit}
          fields={[
            { key: "name", label: "Nome" },
            { key: "owner", label: "Responsável", default: "owner" },
            { key: "content", label: "Conteúdo", type: "textarea" },
            { key: "active", label: "Activa", type: "boolean" },
          ]}
          onClose={() => setEdit(null)}
          save={async (data) => {
            await (edit.id
              ? api.put(`/policies/${edit.id}`, data)
              : api.post("/policies", data));
            await qc.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
function Catalog() {
  const query = useData("/catalog");
  const qc = useQueryClient();
  const [edit, setEdit] = useState<Row | null>(null);
  const can = ["ADMIN", "DATA_OWNER"].includes(useContext(Auth).user!.role);
  return (
    <State loading={query.isPending} error={query.error}>
      <div className="catalog-grid">
        {query.data?.items.map((r: Row) => (
          <section className="panel" key={r.id}>
            <div className="section-title">
              <div className="dataset-heading">
                <Database />
                <h3>{r.name}</h3>
              </div>
              <Badge value={r.classification} />
            </div>
            <p>{r.description}</p>
            <dl>
              <dt>Origem</dt>
              <dd>{r.source}</dd>
              <dt>Responsável</dt>
              <dd>
                {r.owner} / {r.steward}
              </dd>
              <dt>Actualização</dt>
              <dd>{date(r.updated_at)}</dd>
              <dt>Regras associadas</dt>
              <dd>{r.rules.join(", ") || "—"}</dd>
              <dt>Processos ETL</dt>
              <dd>{r.etl_runs.join(", ") || "Nenhum"}</dd>
            </dl>
            <Table
              rows={r.fields}
              columns={[
                ["name", "Campo"],
                ["type", "Tipo"],
                ["classification", "Classificação"],
              ]}
            />
            {can && (
              <button className="secondary" onClick={() => setEdit(r)}>
                Editar metadados
              </button>
            )}
          </section>
        ))}
      </div>
      {edit && (
        <Editor
          title="Metadados e responsabilidades"
          initial={edit}
          fields={[
            { key: "owner", label: "Data Owner" },
            { key: "steward", label: "Data Steward" },
            { key: "engineer", label: "Engenheiro" },
            { key: "auditor", label: "Auditor" },
            {
              key: "classification",
              label: "Classificação",
              options: ["PÚBLICA", "INTERNA", "CONFIDENCIAL", "RESTRITA"],
            },
            { key: "fields", label: "Campos (JSON)", type: "json" },
          ]}
          onClose={() => setEdit(null)}
          save={async (data) => {
            await api.put(`/catalog/${edit.id}`, data);
            await qc.invalidateQueries();
          }}
        />
      )}
    </State>
  );
}
function Lineage() {
  const [batch, setBatch] = useState(""),
    [tx, setTx] = useState(""),
    [selected, setSelected] = useState<Row | null>(null);
  const batches = useData("/batches");
  const query = useData(
    `/lineage?${tx ? `transaction_id=${tx}` : `batch_id=${batch}`}`,
  );
  const nodes = (query.data?.nodes ?? []).map((n: Row, i: number) => ({
    id: n.id,
    position: { x: i * 250, y: 80 + (i % 2) * 60 },
    data: {
      label: (
        <div>
          <small>{n.kind}</small>
          <strong>{n.name}</strong>
          <span>{n.status}</span>
        </div>
      ),
    },
    style: {
      width: 210,
      border: "1px solid #ccd8e3",
      borderRadius: 10,
      padding: 14,
      background: "#fff",
      color: "#18344f",
    },
  }));
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <div>
            <h3>O percurso dos dados, com evidência</h3>
            <p>
              Nós e dependências persistidos durante importações, validações e
              execuções ETL.
            </p>
          </div>
          <GitBranch />
        </div>
        <div className="inline-form">
          <select
            aria-label="Lote de linhagem"
            value={batch}
            onChange={(e) => {
              setBatch(e.target.value);
              setTx("");
            }}
          >
            <option value="">Último lote</option>
            {batches.data?.items.map((r: Row) => (
              <option key={r.id} value={r.id}>
                #{r.id} · {r.filename}
              </option>
            ))}
          </select>
          <input
            aria-label="Transacção a rastrear"
            type="number"
            min="1"
            placeholder="ID interno da transacção"
            value={tx}
            onChange={(e) => setTx(e.target.value)}
          />
        </div>
        <State loading={query.isPending} error={query.error}>
          {nodes.length ? (
            <div className="flow">
              <ReactFlow
                key={`${batch}-${tx}-${nodes.length}`}
                nodes={nodes}
                edges={(query.data?.edges ?? []).map((e: Row) => ({
                  id: String(e.id),
                  source: e.source,
                  target: e.target,
                  animated: true,
                  label: e.description,
                  markerEnd: { type: MarkerType.ArrowClosed },
                  style: { stroke: "#537b9d" },
                }))}
                fitView
                onNodeClick={(_, n) =>
                  setSelected(query.data?.nodes.find((x: Row) => x.id === n.id))
                }
              >
                <Background gap={24} color="#dce4eb" />
                <Controls />
              </ReactFlow>
            </div>
          ) : (
            <Empty />
          )}
        </State>
      </section>
      {query.data?.trace && (
        <section className="panel">
          <h3>Linhagem ao nível do registo</h3>
          <dl>
            {Object.entries(query.data.trace).map(([k, v]) => (
              <React.Fragment key={k}>
                <dt>{k}</dt>
                <dd>{fmt(v)}</dd>
              </React.Fragment>
            ))}
          </dl>
        </section>
      )}
      {selected && (
        <Modal title={selected.name} onClose={() => setSelected(null)}>
          <dl>
            {Object.entries(selected).map(([k, v]) => (
              <React.Fragment key={k}>
                <dt>{k}</dt>
                <dd>{fmt(v)}</dd>
              </React.Fragment>
            ))}
          </dl>
        </Modal>
      )}
    </>
  );
}
function Incidents() {
  const [status, setStatus] = useState(""),
    [offset, setOffset] = useState(0),
    [edit, setEdit] = useState<Row | null>(null),
    [detail, setDetail] = useState<Row | null>(null);
  const query = useData(`/incidents?status=${status}&offset=${offset}`);
  const qc = useQueryClient(),
    user = useContext(Auth).user!;
  const transitions: Record<string, string[]> = {
    OPEN: ["ASSIGNED"],
    ASSIGNED: ["IN_PROGRESS"],
    IN_PROGRESS: ["PENDING_VALIDATION"],
    PENDING_VALIDATION: ["RESOLVED", "IN_PROGRESS"],
    RESOLVED: ["CLOSED"],
  };
  return (
    <>
      <div className="toolbar">
        <p>Detectar → atribuir → corrigir → validar → auditar → encerrar</p>
        <select
          aria-label="Estado dos incidentes"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">Todos os estados</option>
          {[
            "OPEN",
            "ASSIGNED",
            "IN_PROGRESS",
            "PENDING_VALIDATION",
            "RESOLVED",
            "CLOSED",
          ].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </div>
      <section className="panel flush">
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "ID"],
              ["title", "Incidente"],
              ["row_id", "Linha"],
              ["severity", "Criticidade"],
              ["assignee", "Responsável"],
              ["status", "Estado"],
              ["due_at", "Prazo"],
            ]}
            action={(r) => (
              <>
                <button className="text-btn" onClick={() => setDetail(r)}>
                  Histórico
                </button>
                {["ADMIN", "DATA_STEWARD"].includes(user.role) &&
                  transitions[r.status] && (
                    <button className="text-btn" onClick={() => setEdit(r)}>
                      Tratar
                    </button>
                  )}
              </>
            )}
          />
          <Pagination
            offset={offset}
            total={query.data?.total ?? 0}
            setOffset={setOffset}
          />
        </State>
      </section>
      {edit && (
        <Editor
          title={`Tratar incidente #${edit.id}`}
          initial={{ ...edit, status: transitions[edit.status][0] }}
          fields={[
            {
              key: "status",
              label: "Próximo estado",
              options: transitions[edit.status],
            },
            {
              key: "assignee",
              label: "Utilizador responsável",
              optional: true,
              default: "steward",
            },
            {
              key: "evidence",
              label: "Evidência da correcção",
              type: "textarea",
              optional: true,
            },
          ]}
          onClose={() => setEdit(null)}
          save={async (data) => {
            await api.patch(`/incidents/${edit.id}`, data);
            await qc.invalidateQueries();
          }}
        />
      )}
      {detail && (
        <Modal
          title={`Incidente #${detail.id}`}
          onClose={() => setDetail(null)}
        >
          <p>{detail.description}</p>
          <p>
            Regra #{detail.rule_id} · linha staging #{detail.row_id}
          </p>
          <p>{detail.evidence || "Sem evidência registada"}</p>
          <Table
            rows={detail.history}
            columns={[
              ["status", "Estado"],
              ["at", "Data"],
              ["by", "Utilizador"],
              ["validated_run_id", "Validação"],
            ]}
          />
        </Modal>
      )}
    </>
  );
}
function AuditPage() {
  const [action, setAction] = useState(""),
    [offset, setOffset] = useState(0);
  const query = useData(
    `/audit?action=${encodeURIComponent(action)}&offset=${offset}`,
  );
  return (
    <>
      <div className="toolbar">
        <p>
          Registos persistentes de leitura. Não existem operações de alteração
          ou remoção.
        </p>
        <input
          aria-label="Acção"
          placeholder="Filtrar acção exacta, ex.: LOGIN"
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setOffset(0);
          }}
        />
      </div>
      <section className="panel flush">
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "ID"],
              ["username", "Utilizador"],
              ["action", "Acção"],
              ["entity", "Entidade"],
              ["entity_id", "Referência"],
              ["result", "Resultado"],
              ["created_at", "Data"],
              ["details", "Metadados"],
            ]}
          />
          <Pagination
            offset={offset}
            total={query.data?.total ?? 0}
            setOffset={setOffset}
          />
        </State>
      </section>
    </>
  );
}
function Reports() {
  const query = useData("/reports");
  const [currency, setCurrency] = useState("MZN");
  const d = query.data;
  return (
    <State loading={query.isPending} error={query.error}>
      <div className="toolbar">
        <p>
          Valores exactos por moeda. Granularidade: uma linha por transacção
          válida COMPLETED.
        </p>
        <select
          aria-label="Moeda de relatório"
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
        >
          {["MZN", "USD", "ZAR", "EUR"].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </div>
      {[
        ["daily", "Volume financeiro diário", "day", "Dia"],
        ["monthly", "Evolução mensal", "month", "Mês"],
        ["operations", "Distribuição por operação", "operation", "Operação"],
      ].map(([key, title, column, label]) => (
        <section className="panel" key={key}>
          <h3>{title}</h3>
          <Table
            rows={(d?.[key] ?? []).filter((r: Row) => r.currency === currency)}
            columns={[
              [column, label],
              ["currency", "Moeda"],
              ["quantity", "Transacções"],
              ["volume", "Volume financeiro"],
            ]}
          />
        </section>
      ))}
      <section className="panel">
        <h3>Reconciliações por execução</h3>
        <Table
          rows={(d?.reconciliation ?? []).flatMap((r: Row) =>
            r.entries.map((e: Row) => ({
              ...e,
              run_id: r.run_id,
              batch_id: r.batch_id,
            })),
          )}
          columns={[
            ["run_id", "ETL"],
            ["batch_id", "Lote"],
            ["currency", "Moeda"],
            ["source", "Origem elegível"],
            ["warehouse", "Warehouse"],
            ["difference", "Diferença"],
          ]}
        />
      </section>
    </State>
  );
}
function UsersPage() {
  const query = useData("/users");
  const [edit, setEdit] = useState<Row | null>(null);
  const qc = useQueryClient();
  return (
    <>
      <div className="toolbar">
        <p>
          Permissões verificadas no backend. Alterações revogam sessões
          existentes.
        </p>
        <button onClick={() => setEdit({})}>
          <Plus size={16} />
          Novo utilizador
        </button>
      </div>
      <section className="panel flush">
        <State loading={query.isPending} error={query.error}>
          <Table
            rows={query.data?.items ?? []}
            columns={[
              ["id", "ID"],
              ["username", "Utilizador"],
              ["full_name", "Nome"],
              ["role", "Perfil"],
              ["active", "Activo"],
            ]}
            action={(r) => (
              <button className="text-btn" onClick={() => setEdit(r)}>
                Permissões
              </button>
            )}
          />
        </State>
      </section>
      {edit && (
        <Editor
          title={edit.id ? "Alterar permissões" : "Criar utilizador"}
          initial={edit}
          fields={[
            ...(!edit.id
              ? [
                  { key: "username", label: "Utilizador" },
                  { key: "full_name", label: "Nome" },
                  {
                    key: "password",
                    label: "Palavra-passe (mín. 12 caracteres)",
                    type: "password",
                  },
                ]
              : []),
            {
              key: "role",
              label: "Perfil",
              options: [
                "ADMIN",
                "DATA_OWNER",
                "DATA_STEWARD",
                "DATA_ENGINEER",
                "AUDITOR",
              ],
            },
            ...(edit.id
              ? [{ key: "active", label: "Activo", type: "boolean" }]
              : []),
          ]}
          onClose={() => setEdit(null)}
          save={async (data) => {
            await (edit.id
              ? api.patch(`/users/${edit.id}`, data)
              : api.post("/users", data));
            await qc.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
export function Protected({ children }: { children: ReactNode }) {
  const auth = useContext(Auth);
  return auth.user ? <>{children}</> : <Navigate to="/login" replace />;
}
function Layout() {
  const auth = useContext(Auth),
    location = useLocation();
  const [menu, setMenu] = useState(false),
    [password, setPassword] = useState(false);
  const pageTitle =
    nav.find(([path]) => path === location.pathname)?.[1] ?? "MobiFin";
  return (
    <div className="app-shell">
      <aside className={menu ? "sidebar open" : "sidebar"}>
        <NavLink to="/" className="brand">
          <span className="brand-icon">
            <Activity />
          </span>
          MobiFin<span className="brand-dot">.</span>
        </NavLink>
        <div className="workspace-tag">
          <span /> Data Management <small>ACADEMIC</small>
        </div>
        <div className="nav-label">PLATAFORMA</div>
        <nav>
          {nav
            .filter(([path]) => path != "/users" || auth.user?.role === "ADMIN")
            .filter(
              ([path]) =>
                path != "/audit" ||
                ["ADMIN", "AUDITOR"].includes(auth.user?.role ?? ""),
            )
            .map(([path, label, Icon], i) => (
              <React.Fragment key={path}>
                {i === 4 && <div className="nav-label">GESTÃO E CONTROLO</div>}
                <NavLink
                  to={path}
                  end={path === "/"}
                  onClick={() => setMenu(false)}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </NavLink>
              </React.Fragment>
            ))}
        </nav>
        <div className="sidebar-footer">
          <ShieldCheck size={17} />
          <span>
            Ambiente de demonstração
            <br />
            <small>ISUTC · Engenharia de Dados</small>
          </span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <button
              className="icon mobile-menu"
              onClick={() => setMenu(!menu)}
              aria-label="Abrir menu"
            >
              <Menu />
            </button>
            <span className="breadcrumb">
              Plataforma <ChevronRight size={14} />
              <strong>{pageTitle}</strong>
            </span>
          </div>
          <div className="profile">
            <span className="avatar">{auth.user?.full_name.slice(0, 1)}</span>
            <span>
              <strong>{auth.user?.full_name}</strong>
              <small>{auth.user?.role.replaceAll("_", " ")}</small>
            </span>
            <button
              className="icon"
              title="Alterar palavra-passe"
              aria-label="Alterar palavra-passe"
              onClick={() => setPassword(true)}
            >
              <KeyRound size={17} />
            </button>
            <button
              className="icon"
              onClick={auth.logout}
              aria-label="Terminar sessão"
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>
        <main>
          <div className="page-title">
            <div>
              <span className="eyebrow">MOBIFIN DATA MANAGEMENT</span>
              <h1>{pageTitle}</h1>
            </div>
            <span className="synthetic">
              <ShieldCheck size={14} /> Dados sintéticos
            </span>
          </div>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/clients" element={<Operational kind="clients" />} />
            <Route
              path="/transactions"
              element={<Operational kind="transactions" />}
            />
            <Route path="/imports" element={<Imports />} />
            <Route path="/governance" element={<Governance />} />
            <Route path="/catalog" element={<Catalog />} />
            <Route path="/quality" element={<Quality />} />
            <Route path="/validations" element={<Validations />} />
            <Route path="/lineage" element={<Lineage />} />
            <Route path="/etl" element={<ETL />} />
            <Route path="/incidents" element={<Incidents />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
          <footer className="page-footer">
            MobiFin, Lda. · Plataforma académica de Engenharia de Dados
            <span>Governar. Conhecer. Confiar.</span>
          </footer>
        </main>
      </div>
      {password && (
        <Editor
          title="Alterar palavra-passe"
          fields={[
            {
              key: "current_password",
              label: "Palavra-passe actual",
              type: "password",
            },
            {
              key: "new_password",
              label: "Nova palavra-passe (mín. 12 caracteres)",
              type: "password",
            },
          ]}
          onClose={() => setPassword(false)}
          save={async (data) => {
            await api.post("/auth/password", data);
            auth.logout();
          }}
        />
      )}
    </div>
  );
}
const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});
export function App() {
  const [user, setUser] = useState<Person | null>(null);
  function login(token: string, person: Person) {
    setToken(token);
    setUser(person);
  }
  async function logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      setToken("");
      setUser(null);
      client.clear();
    }
  }
  return (
    <QueryClientProvider client={client}>
      <Auth.Provider value={{ user, login, logout }}>
        <BrowserRouter>
          <Routes>
            <Route
              path="/login"
              element={user ? <Navigate to="/" replace /> : <Login />}
            />
            <Route
              path="*"
              element={
                <Protected>
                  <Layout />
                </Protected>
              }
            />
          </Routes>
        </BrowserRouter>
      </Auth.Provider>
    </QueryClientProvider>
  );
}
const root = document.getElementById("root");
if (root)
  createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
