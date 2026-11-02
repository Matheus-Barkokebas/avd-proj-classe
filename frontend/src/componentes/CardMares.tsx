import { useMareProximas } from "../api/consultas";
import { dataHora, numero } from "../formato";
import { Carregando, ErroCarga, Vazio } from "./Estados";
import { Card } from "./Pecas";

export function CardMares() {
  const mares = useMareProximas();
  return (
    <Card titulo="Próximas marés" sub="tábua do COP">
      {mares.isPending ? <Carregando /> : mares.error ? <ErroCarga erro={mares.error} tentarDeNovo={() => mares.refetch()} /> :
       !mares.data.length ? <Vazio texto="Sem marés na tábua para os próximos dias." /> : (
        <dl className="kv">
          {mares.data.slice(0, 6).map((m) => [
            <dt key={`${m.data_hora}-quando`}>{m.tipo === "alta" ? <b>Alta</b> : "Baixa"} · {dataHora(m.data_hora)}</dt>,
            <dd key={`${m.data_hora}-altura`}>{numero(m.mare_m, 2)} m</dd>,
          ])}
        </dl>
      )}
    </Card>
  );
}
