# ⚡ E-Redes Cortes – Integração para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/O_TEU_USER/ha-eredes-cortes)](https://github.com/O_TEU_USER/ha-eredes-cortes/releases)
[![Validate](https://github.com/O_TEU_USER/ha-eredes-cortes/actions/workflows/validate.yml/badge.svg)](https://github.com/O_TEU_USER/ha-eredes-cortes/actions/workflows/validate.yml)

Integração personalizada para o [Home Assistant](https://www.home-assistant.io/) que mostra as **interrupções de energia programadas** (obras na rede) da E-Redes para as localizações que escolheres.

> **Aviso:** este projeto é **não oficial** e não tem qualquer relação com a E-Redes. O nome E-Redes e o respetivo logótipo são marcas dos seus titulares. Os dados são obtidos de fontes públicas da E-Redes e a sua disponibilidade e exatidão não são garantidas por este projeto.

## Funcionalidades

- Um sensor por localização (filtro) configurada.
- O **estado** do sensor é o número de intervenções registadas.
- O atributo `interrupcoes` traz a lista de cortes (freguesia, código postal, início, fim e duração).
- Compatível com cartões do dashboard e automações (ex.: notificação por Telegram quando surge um corte novo).

## Instalação

### Via HACS (recomendado)

1. No Home Assistant, abre **HACS → ⋮ → Repositórios personalizados**.
2. Adiciona `https://github.com/O_TEU_USER/ha-eredes-cortes` com a categoria **Integração**.
3. Procura **E-Redes Cortes**, instala e **reinicia o Home Assistant**.

[![Abrir no HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=O_TEU_USER&repository=ha-eredes-cortes&category=integration)

### Instalação manual

1. Copia a pasta `custom_components/eredes_cortes` para a pasta `custom_components` da tua instalação.
2. Reinicia o Home Assistant.

## Configuração

1. Vai a **Definições → Dispositivos e serviços → Adicionar integração**.
2. Procura **E-Redes Cortes**.
3. Segue o assistente e indica a localização/filtro pretendido (concelho, freguesia ou código postal).

Podes adicionar a integração várias vezes para acompanhar várias localizações. Cada uma cria um sensor próprio.


## Entidades e atributos

| Entidade | Estado | Descrição |
| :--- | :--- | :--- |
| `sensor.…` | Número de intervenções | Um sensor por localização configurada |

Atributos principais:

| Atributo | Descrição |
| :--- | :--- |
| `filtro_aplicado` | Filtro usado nessa localização |
| `interrupcoes` | Lista de interrupções (ver abaixo) |

Cada elemento de `interrupcoes`:

```yaml
- municipality: Lisboa
  parish: Campolide
  zipcode: 1070-003
  data: '2026-11-15'
  startdatetime: '2026-11-15T05:00:00'
  enddatetime: '2026-11-15T08:00:00'
  durationallocation: '180'   # minutos
```

> ⚠️ **Limitação conhecida:** o atributo `interrupcoes` pode conter menos entradas do que o estado do sensor (por exemplo, 10 entradas para 40 intervenções). Isto vem do limite aplicado aos dados. Cartões e automações baseados no atributo só veem as entradas disponíveis.

## Exemplo: cartão para o dashboard

Mostra um quadrado por entidade, com:

- **Topo:** freguesia e código postal.
- **Centro:** a data mais próxima de corte.
- **Rodapé:** número de intervenções. Tocar abre o detalhe.
- **Cores:** 🟢 sem cortes · 🟡 há cortes, mas não nos próximos 7 dias · 🔴 há corte nos próximos 7 dias (ou em curso).

**Requisitos (HACS, Frontend):** [auto-entities](https://github.com/thomasloven/lovelace-auto-entities), [button-card](https://github.com/custom-cards/button-card) e [Browser Mod](https://github.com/thomasloven/hass-browser_mod) (versão 2.x, para o popup).

```yaml
type: custom:auto-entities
card:
  type: grid
  columns: 2
  square: false
card_param: cards
filter:
  include:
    - integration: eredes_cortes
      domain: sensor
      options:
        type: custom:button-card
        entity: this.entity_id
        icon: mdi:flash-alert
        show_state: false
        show_label: true
        aspect_ratio: 1/0.7
        name: |
          [[[
            var a = entity.attributes;
            var items = a.interrupcoes || [];
            function uniq(k) {
              var seen = [];
              items.forEach(function (i) {
                var v = i[k];
                if (v && seen.indexOf(v) < 0) seen.push(v);
              });
              return seen;
            }
            var parishes = uniq('parish');
            var zips = uniq('zipcode');
            var parts = [];
            if (parishes.length) {
              parts.push(parishes.length > 2
                ? parishes.slice(0, 2).join(', ') + ' +' + (parishes.length - 2)
                : parishes.join(', '));
            }
            if (zips.length) {
              parts.push(zips.length > 1
                ? zips[0] + ' (+' + (zips.length - 1) + ')'
                : zips[0]);
            }
            if (parts.length) return parts.join(' · ');
            return a.filtro_aplicado || a.friendly_name || entity.entity_id;
          ]]]
        label: |
          [[[
            var items = entity.attributes.interrupcoes || [];
            if (items.length === 0) return "Sem cortes";
            var starts = items
              .map(function (i) { return String(i.startdatetime || ''); })
              .filter(function (s) { return s.length >= 10; })
              .sort();
            if (starts.length === 0) return "?";
            var p = starts[0].substring(0, 10).split('-');
            return p[2] + '/' + p[1] + '/' + p[0];
          ]]]
        custom_fields:
          footer: |
            [[[
              var n = parseInt(entity.state, 10);
              if (isNaN(n)) n = (entity.attributes.interrupcoes || []).length;
              var txt = n === 0 ? "Sem intervenções" : n + (n === 1 ? " intervenção" : " intervenções");
              return `<div style="display:flex;justify-content:space-between;align-items:center;width:100%;">
                        <span>${txt}</span>
                        <ha-icon icon="mdi:arrow-right-circle-outline" style="--mdc-icon-size:28px;"></ha-icon>
                      </div>`;
            ]]]
        tap_action:
          action: call-service
          service: browser_mod.popup
          service_data:
            title: Interrupções
            size: wide
            content:
              type: markdown
              content: |
                {% set items = state_attr('this.entity_id','interrupcoes') or [] %}
                {% set total = states('this.entity_id') | int(0) %}
                ### {{ state_attr('this.entity_id','friendly_name') }}
                {% if total > items | length %}
                > ⚠️ A mostrar {{ items | length }} de {{ total }} intervenções.
                {% endif %}

                | Freguesia | Código Postal | Início | Fim | Duração (min) |
                | :--- | :--- | :--- | :--- | :--- |
                {% for item in items -%}
                | {{ item.parish or '-' }} | `{{ item.zipcode or '-' }}` | {{ item.startdatetime | as_timestamp | timestamp_custom('%d/%m/%Y %H:%M', true, '-') }} | {{ item.enddatetime | as_timestamp | timestamp_custom('%d/%m/%Y %H:%M', true, '-') }} | {{ item.durationallocation or '-' }} |
                {% endfor %}
        styles:
          grid:
            - grid-template-areas: '"n" "l" "footer"'
            - grid-template-columns: 1fr
            - grid-template-rows: min-content 1fr min-content
          card:
            - border-radius: 12px
            - padding: 0
            - color: white
            - position: relative
            - overflow: hidden
            - background-color: |
                [[[
                  var items = entity.attributes.interrupcoes || [];
                  if (items.length === 0) return '#2ecc71';          // Verde: sem cortes
                  var now = new Date();
                  var week = new Date(now.getTime() + 7*24*3600*1000);
                  var thisWeek = items.some(function (i) {
                    var s = new Date(String(i.startdatetime).replace(' ', 'T'));
                    var e = new Date(String(i.enddatetime).replace(' ', 'T'));
                    return s <= week && e >= now;                    // Começa nos próximos 7 dias ou está em curso
                  });
                  return thisWeek ? '#e74c3c' : '#f39c12';           // Vermelho / Amarelo
                ]]]
          icon:
            - position: absolute
            - right: -12px
            - top: 22%
            - width: 110px
            - opacity: 0.15
          name:
            - position: relative
            - z-index: 1
            - font-weight: bold
            - font-size: 15px
            - align-self: start
            - justify-self: start
            - text-align: left
            - white-space: normal
            - padding: 14px 16px 0 16px
          label:
            - position: relative
            - z-index: 1
            - font-size: 24px
            - font-weight: bold
            - align-self: center
            - justify-self: start
            - padding: 0 16px
          custom_fields:
            footer:
              - position: relative
              - z-index: 1
              - background-color: rgba(0, 0, 0, 0.15)
              - padding: 10px 16px
              - font-size: 12px
              - width: 100%
              - box-sizing: border-box
```

**Notas**

- O `title` do popup é texto fixo, porque o Browser Mod não processa Jinja nesse campo. O nome da entidade aparece como cabeçalho dentro do markdown.
- Para quadrados mais altos ou mais baixos, ajusta o `aspect_ratio` (por exemplo `1/1` ou `1/0.6`).

## Exemplo: notificação por Telegram quando surge um corte novo

A automação compara a lista de `interrupcoes` antes e depois de cada atualização e só envia as entradas que não existiam. Cada entrada é identificada por código postal, início e fim.

Substitui as entidades e o serviço de notificação pelos teus.

```yaml
alias: E-Redes - novo corte programado
mode: queued
max_exceeded: silent
triggers:
  - trigger: state
    entity_id:
      - sensor.SUBSTITUI_PELA_TUA_ENTIDADE_1
      - sensor.SUBSTITUI_PELA_TUA_ENTIDADE_2
conditions:
  # Ignora arranques/reloads
  - condition: template
    value_template: >
      {{ trigger.from_state is not none
         and trigger.from_state.state not in ['unavailable', 'unknown']
         and trigger.to_state.state not in ['unavailable', 'unknown'] }}
actions:
  - variables:
      old_items: "{{ trigger.from_state.attributes.interrupcoes | default([], true) }}"
      new_items: "{{ trigger.to_state.attributes.interrupcoes | default([], true) }}"
      old_keys: >-
        {%- set ns = namespace(k=[]) -%}
        {%- for i in old_items -%}
          {%- set ns.k = ns.k + [[i.zipcode, i.startdatetime, i.enddatetime] | join('|')] -%}
        {%- endfor -%}
        {{ ns.k }}
      novos: >-
        {%- set ns = namespace(n=[]) -%}
        {%- for i in new_items -%}
          {%- if ([i.zipcode, i.startdatetime, i.enddatetime] | join('|')) not in old_keys -%}
            {%- set ns.n = ns.n + [i] -%}
          {%- endif -%}
        {%- endfor -%}
        {{ ns.n }}
  - condition: template
    value_template: "{{ novos | length > 0 }}"
  - action: notify.SUBSTITUI_PELO_TEU_NOTIFY_TELEGRAM
    data:
      message: >-
        ⚡ Novo(s) corte(s) programado(s) ({{ novos | length }})
        {% for i in novos[:10] %}
        • {{ i.parish or '-' }} ({{ i.zipcode or '-' }}): {{ i.startdatetime[8:10] }}/{{ i.startdatetime[5:7] }}/{{ i.startdatetime[0:4] }} {{ i.startdatetime[11:16] }}–{{ i.enddatetime[11:16] }}
        {% endfor %}
        {% if novos | length > 10 %}… e mais {{ novos | length - 10 }}{% endif %}
```

**Limitações**

- A comparação é feita entre duas atualizações seguidas e nada fica guardado em disco. Um corte que surja durante um reinício do Home Assistant pode passar despercebido.
- Se o atributo tiver um limite de entradas, uma entrada que antes estava escondida pode ser considerada nova.

## Resolução de problemas

| Problema | Possível causa e solução |
| :--- | :--- |
| O popup não abre | Verifica se o Browser Mod 2.x está instalado, a integração configurada e o browser recarregado. Testa `browser_mod.popup` em **Ferramentas de programador → Ações**. |
| O cartão fica vazio | Confirma que o `card_param` é `cards` (grid) e que o filtro `integration: eredes_cortes` devolve entidades. |
| Só aparecem 10 entradas | O limite está nos dados da integração. Ver "Limitação conhecida". |

## Contribuir

Contribuições são bem-vindas. Abre um [issue](https://github.com/O_TEU_USER/ha-eredes-cortes/issues) para reportar problemas ou sugerir melhorias, ou envia um *pull request*. Ao reportar um erro, junta a versão do Home Assistant e os logs relevantes (**Definições → Sistema → Registos**), sem dados pessoais.

## Licença

Distribuído sob a licença MIT. Ver o ficheiro [LICENSE](LICENSE).

## Agradecimentos

Dados públicos disponibilizados pela E-Redes. Projeto independente e sem afiliação à E-Redes.
