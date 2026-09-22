# -*- coding: utf-8 -*-
"""
TECHSECURE S.A. -- SALA DE CONTROLE DE INCIDENTES
Simulacao imersiva em Pygame para dinamicas de conscientizacao em
ciberseguranca. O jogador atua como Analista de Plantao e precisa
investigar tres servidores comprometidos antes que o tempo acabe ou a
integridade da rede corporativa chegue a zero.

LAYOUT:
  - HUD SUPERIOR: cronometro regressivo em tempo real + barra de
    Integridade da Rede Corporativa (comeca em 100%).
  - PAINEL ESQUERDO: lista dos servidores afetados (SRV-RH01, SRV-FIN02,
    SRV-PROD03), cada um com um indicador de status.
  - PAINEL DIREITO (Terminal de Auditoria): exibe o log/codigo-fonte
    capturado no servidor selecionado, com pistas sobre o tipo de
    gatilho (Bomba Logica x Bomba Relogio), revelado com efeito de
    maquina de escrever.

IMPORTANTE: todo o conteudo (logs, codigo) e ficticio e ilustrativo,
criado apenas para fins didaticos. Nao ha codigo malicioso real nem
tecnicas de invasao.

Controles:
  - Mouse: selecionar servidor / clicar em BOMBA LOGICA ou BOMBA RELOGIO
  - ESPACO: avancar a sequencia de inicializacao / tela final -> reinicio
  - R: reiniciar apos a tela final
  - ESC: sair
"""

import pygame
import random
import sys
import math

pygame.init()

# ---------------------------------------------------------------------------
# Configuracao geral
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1150, 760
FPS = 60

GLOBAL_TIME = 240.0          # 4 minutos de missao
INTEGRITY_START = 100
WRONG_PENALTY = 15
CONNECT_TIME = 1.3           # duracao da animacao de "conectando..."
FEEDBACK_HOLD = 3.5           # segundos mostrando o resultado do diagnostico

BG = (5, 7, 11)
PANEL_BG = (13, 17, 26)
TERMINAL_BG = (9, 12, 18)
NEON_CYAN = (60, 230, 220)
NEON_GREEN = (80, 240, 140)
NEON_PINK = (255, 70, 140)
NEON_YELLOW = (250, 220, 90)
NEON_RED = (255, 70, 70)
NEON_PURPLE = (170, 120, 255)
GRID_LINE = (18, 40, 40)
TEXT_MAIN = (208, 238, 233)
TEXT_DIM = (100, 140, 140)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TechSecure S.A. - Sala de Controle de Incidentes")
clock = pygame.time.Clock()

font_logo = pygame.font.SysFont("consolas", 30, bold=True)
font_title = pygame.font.SysFont("consolas", 34, bold=True)
font_h2 = pygame.font.SysFont("consolas", 21, bold=True)
font_body = pygame.font.SysFont("consolas", 17)
font_small = pygame.font.SysFont("consolas", 14)
font_code = pygame.font.SysFont("consolas", 16)
font_clock = pygame.font.SysFont("consolas", 40, bold=True)
font_mono_rain = pygame.font.SysFont("consolas", 16)


# ---------------------------------------------------------------------------
# Chuva digital (fundo atmosferico)
# ---------------------------------------------------------------------------
RAIN_CHARS = "01LOGICATEMPORELOGIOGATILHO$#@%01010101"

class DigitalRain:
    def __init__(self, width, height, font):
        self.font = font
        self.char_w = 15
        self.cols = width // self.char_w
        self.drops = [random.randint(-40, 0) for _ in range(self.cols)]
        self.speeds = [random.uniform(0.25, 0.9) for _ in range(self.cols)]

    def update_and_draw(self, surface, alpha=45):
        fade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fade.fill((5, 7, 11, alpha))
        surface.blit(fade, (0, 0))
        for i in range(self.cols):
            ch = random.choice(RAIN_CHARS)
            x = i * self.char_w
            y = int(self.drops[i]) * 17
            glyph = self.font.render(ch, True, (30, 130, 100))
            surface.blit(glyph, (x, y))
            self.drops[i] += self.speeds[i]
            if y > HEIGHT and random.random() > 0.975:
                self.drops[i] = random.randint(-20, 0)


rain = DigitalRain(WIDTH, HEIGHT, font_mono_rain)


def draw_background():
    rain.update_and_draw(screen, alpha=60)
    step = 42
    for x in range(0, WIDTH, step):
        pygame.draw.line(screen, GRID_LINE, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, step):
        pygame.draw.line(screen, GRID_LINE, (0, y), (WIDTH, y), 1)


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------
def draw_text(surface, text, font, color, x, y, center=False):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(x, y)) if center else surf.get_rect(topleft=(x, y))
    surface.blit(surf, rect)
    return rect


def wrap_text(text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] > max_width:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def neon_panel(rect, border_color, bg_color=PANEL_BG, width=2, radius=10):
    pygame.draw.rect(screen, bg_color, rect, border_radius=radius)
    pygame.draw.rect(screen, border_color, rect, width=width, border_radius=radius)


class Typewriter:
    def __init__(self, text="", chars_per_sec=70):
        self.full_text = text
        self.chars_per_sec = chars_per_sec
        self.elapsed = 0.0

    def reset(self, text=None):
        if text is not None:
            self.full_text = text
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt

    def visible_len(self):
        return int(self.elapsed * self.chars_per_sec)

    def done(self):
        return self.visible_len() >= len(self.full_text)


# ---------------------------------------------------------------------------
# Dados dos servidores afetados
# ---------------------------------------------------------------------------
SERVERS = [
    {
        "id": "SRV-RH01",
        "label": "Servidor de Banco de Dados e RH",
        "type": "LOGICA",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-RH01",
            "[AUDITORIA] Extraindo trigger suspeito da tabela 'funcionarios'...",
            "",
            "-- trigger: after_update ON tabela_funcionarios",
            "IF NEW.status_emprego = 'DEMITIDO' THEN",
            "    EXECUTE limpar_registros_criticos(NEW.id_funcionario);",
            "    EXECUTE revogar_credenciais_admin();",
            "END IF;",
            "",
            "[PISTA] O disparo depende de uma mudanca de ESTADO no banco",
            "        de dados (status do funcionario), nao de uma data.",
        ],
        "explain": (
            "Correto: e uma BOMBA LOGICA. O trigger so executa quando uma "
            "CONDICAO de negocio se torna verdadeira (status = 'DEMITIDO'). "
            "Nao ha nenhuma comparacao de data ou hora envolvida -- a "
            "logica reage a um ESTADO do sistema. Esse padrao e associado "
            "a insider threats (MITRE ATT&CK T1485)."
        ),
    },
    {
        "id": "SRV-FIN02",
        "label": "Servidor Financeiro e Agendador Cron",
        "type": "RELOGIO",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-FIN02",
            "[AUDITORIA] Lendo tarefas agendadas em /etc/cron.d/...",
            "",
            "# /etc/cron.d/maintenance",
            "0 3 15 6 * root /opt/scripts/cleanup_all.sh --force",
            "",
            "# cleanup_all.sh executa: rm -rf /data/financeiro/* sem confirmacao",
            "",
            "[PISTA] A tarefa dispara em uma DATA E HORA fixas (dia 15/06,",
            "        03h), independente de qualquer condicao do sistema.",
        ],
        "explain": (
            "Correto: e uma BOMBA RELOGIO. A entrada de cron dispara em "
            "uma data/hora especifica e fixa, sem depender de nenhum "
            "estado do sistema -- padrao classico de gatilho temporal. "
            "O NIST recomenda auditoria periodica de tarefas agendadas em "
            "servidores criticos."
        ),
    },
    {
        "id": "SRV-PROD03",
        "label": "Servidor de Producao",
        "type": "LOGICA",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-PROD03",
            "[AUDITORIA] Analisando processo watchdog em segundo plano...",
            "",
            "# heartbeat esperado a cada check-in do analista responsavel",
            "if dias_desde_ultimo_checkin('analista_producao') > 15:",
            "    liberar_payload_destrutivo()",
            "",
            "[PISTA] O disparo depende da AUSENCIA continuada de uma acao",
            "        humana (check-in), nao de um horario fixo no calendario.",
        ],
        "explain": (
            "Correto: e uma BOMBA LOGICA (variante Dead Man's Switch). O "
            "disparo depende da AUSENCIA de uma acao esperada (check-in do "
            "analista), nao de uma data/hora fixa -- ainda e um gatilho de "
            "ESTADO, so que definido pela falta de um evento. Recomendacao: "
            "monitorar logica condicionada a inatividade de contas "
            "privilegiadas."
        ),
    },
]


# ---------------------------------------------------------------------------
# Sequencia de inicializacao (boot) -- imersao
# ---------------------------------------------------------------------------
BOOT_LINES = [
    "INICIANDO PROTOCOLO DE CONTENCAO TECHSECURE...",
    "CARREGANDO INVENTARIO DE SERVIDORES AFETADOS...",
    "SINCRONIZANDO RELOGIO DE AUDITORIA...",
    "ESTABELECENDO CANAL SEGURO COM O SOC...",
    "3 INCIDENTES ATIVOS DETECTADOS.",
    "INTEGRIDADE DA REDE CORPORATIVA: 100%",
    "AGUARDANDO ANALISTA DE PLANTAO...",
]


# ---------------------------------------------------------------------------
# Estado do jogo
# ---------------------------------------------------------------------------
class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.status = "boot"          # boot, hub, connecting, analyzing, feedback, gameover, victory
        self.boot_index = 0
        self.boot_timer = 0.0
        self.time_left = GLOBAL_TIME
        self.integrity = INTEGRITY_START
        self.servers = [dict(s, state="pendente", attempts=0) for s in SERVERS]
        self.selected = None
        self.connect_timer = 0.0
        self.log_tw = Typewriter()
        self.last_correct = None
        self.last_explain = ""
        self.feedback_timer = 0.0
        self.mistakes = 0
        self.glitch_timer = 0.0

    def secured_count(self):
        return sum(1 for s in self.servers if s["state"] == "secured")

    def select_server(self, index):
        if self.status not in ("hub",):
            return
        self.selected = index
        self.status = "connecting"
        self.connect_timer = 0.0

    def submit_diagnosis(self, kind):
        if self.status != "analyzing" or self.selected is None:
            return
        srv = self.servers[self.selected]
        correct = kind == srv["type"]
        srv["attempts"] += 1
        if correct:
            srv["state"] = "secured"
            self.last_correct = True
        else:
            self.integrity -= WRONG_PENALTY
            self.mistakes += 1
            self.last_correct = False
            self.glitch_timer = 0.5
        self.last_explain = srv["explain"]
        self.status = "feedback"
        self.feedback_timer = FEEDBACK_HOLD

    def back_to_hub_or_end(self):
        if self.integrity <= 0:
            self.status = "gameover"
            return
        if self.secured_count() >= len(self.servers):
            self.status = "victory"
            return
        self.status = "hub"
        self.selected = None

    def update(self, dt):
        if self.status == "boot":
            self.boot_timer += dt
            if self.boot_timer > 0.45:
                self.boot_timer = 0.0
                if self.boot_index < len(BOOT_LINES):
                    self.boot_index += 1
        elif self.status in ("hub", "connecting", "analyzing", "feedback"):
            self.time_left -= dt
            if self.glitch_timer > 0:
                self.glitch_timer -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self.status = "gameover"
                return
            if self.integrity <= 0:
                self.status = "gameover"
                return

            if self.status == "connecting":
                self.connect_timer += dt
                if self.connect_timer >= CONNECT_TIME:
                    self.status = "analyzing"
                    srv = self.servers[self.selected]
                    self.log_tw.reset("\n".join(srv["log"]))
            elif self.status == "analyzing":
                self.log_tw.update(dt)
            elif self.status == "feedback":
                self.feedback_timer -= dt
                if self.feedback_timer <= 0:
                    self.back_to_hub_or_end()


state = GameState()


# ---------------------------------------------------------------------------
# Desenho -- HUD
# ---------------------------------------------------------------------------
def draw_hud():
    danger_time = state.time_left < 30
    danger_integrity = state.integrity < 30

    hud_rect = pygame.Rect(0, 0, WIDTH, 108)
    pygame.draw.rect(screen, (9, 11, 17), hud_rect)
    pygame.draw.line(screen, NEON_CYAN, (0, 108), (WIDTH, 108), 2)

    draw_text(screen, "TECHSECURE S.A. -- SALA DE CONTROLE DE INCIDENTES",
              font_logo, NEON_CYAN, 24, 14)
    draw_text(screen, f"Servidores neutralizados: {state.secured_count()}/{len(state.servers)}   |   Falhas: {state.mistakes}",
              font_small, TEXT_DIM, 24, 50)

    # Cronometro
    mins = int(state.time_left) // 60
    secs = int(state.time_left) % 60
    tcolor = NEON_RED if danger_time else NEON_GREEN
    if danger_time and int(state.time_left * 2) % 2 == 0:
        tcolor = (255, 255, 255)
    draw_text(screen, "TEMPO RESTANTE", font_small, TEXT_DIM, WIDTH - 260, 16)
    draw_text(screen, f"{mins:02d}:{secs:02d}", font_clock, tcolor, WIDTH - 260, 40)

    # Barra de integridade
    bar_x, bar_y, bar_w, bar_h = 24, 76, WIDTH - 320, 22
    draw_text(screen, "INTEGRIDADE DA REDE CORPORATIVA", font_small, TEXT_DIM, bar_x, bar_y - 16)
    pygame.draw.rect(screen, (25, 25, 25), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
    ratio = max(0, state.integrity) / INTEGRITY_START
    icolor = NEON_GREEN if ratio > 0.5 else (NEON_YELLOW if ratio > 0.25 else NEON_RED)
    pygame.draw.rect(screen, icolor, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=6)
    pygame.draw.rect(screen, icolor, (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=6)
    draw_text(screen, f"{max(0, state.integrity)}%", font_small, TEXT_MAIN, bar_x + bar_w + 10, bar_y + 2)

    if danger_time or danger_integrity:
        pulse = (math.sin(pygame.time.get_ticks() / 150) + 1) / 2
        alpha = int(30 + pulse * 40)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 0, 0, alpha))
        screen.blit(overlay, (0, 0))


STATUS_COLORS = {
    "pendente": TEXT_DIM,
    "secured": NEON_GREEN,
    "compromised": NEON_RED,
}
STATUS_LABELS = {
    "pendente": "NAO ANALISADO",
    "secured": "NEUTRALIZADO",
    "compromised": "TENTATIVA FALHOU",
}


def draw_server_list():
    panel = pygame.Rect(20, 128, 330, HEIGHT - 160)
    neon_panel(panel, NEON_PINK)
    draw_text(screen, "SERVIDORES AFETADOS", font_h2, NEON_PINK, panel.x + 16, panel.y + 14)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 16, panel.y + 44), (panel.right - 16, panel.y + 44), 1)

    y = panel.y + 58
    card_h = 110
    for i, srv in enumerate(state.servers):
        rect = pygame.Rect(panel.x + 14, y, panel.width - 28, card_h)
        selected = (state.selected == i and state.status in ("connecting", "analyzing", "feedback"))
        border = NEON_YELLOW if selected else STATUS_COLORS.get(
            "secured" if srv["state"] == "secured" else ("compromised" if srv["attempts"] > 0 and srv["state"] != "secured" else "pendente"),
            TEXT_DIM)
        neon_panel(rect, border, bg_color=(16, 18, 26), width=2, radius=8)

        dot_color = NEON_GREEN if srv["state"] == "secured" else (NEON_RED if srv["attempts"] > 0 else TEXT_DIM)
        pygame.draw.circle(screen, dot_color, (rect.x + 18, rect.y + 20), 7)

        draw_text(screen, srv["id"], font_body, NEON_CYAN, rect.x + 34, rect.y + 10)
        for j, line in enumerate(wrap_text(srv["label"], font_small, rect.width - 46)):
            draw_text(screen, line, font_small, TEXT_MAIN, rect.x + 34, rect.y + 34 + j * 18)

        status_key = "secured" if srv["state"] == "secured" else ("compromised" if srv["attempts"] > 0 else "pendente")
        draw_text(screen, STATUS_LABELS[status_key], font_small, STATUS_COLORS[status_key],
                  rect.x + 34, rect.bottom - 22)

        y += card_h + 14


# ---------------------------------------------------------------------------
# Painel direito -- terminal de auditoria
# ---------------------------------------------------------------------------
def diagnosis_button_rects(panel):
    w, h = 260, 56
    gap = 30
    y = panel.bottom - 90
    x1 = panel.centerx - w - gap // 2
    x2 = panel.centerx + gap // 2
    return {
        "LOGICA": pygame.Rect(x1, y, w, h),
        "RELOGIO": pygame.Rect(x2, y, w, h),
    }


def draw_terminal_idle(panel):
    draw_text(screen, "TERMINAL DE AUDITORIA", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)
    draw_text(screen, "Selecione um servidor na lista a esquerda para iniciar a", font_body, TEXT_DIM,
              panel.x + 20, panel.y + 80)
    draw_text(screen, "captura e analise do log de auditoria.", font_body, TEXT_DIM,
              panel.x + 20, panel.y + 104)
    if int(pygame.time.get_ticks() / 500) % 2 == 0:
        draw_text(screen, "_", font_body, NEON_GREEN, panel.x + 20, panel.y + 140)


def draw_terminal_connecting(panel):
    srv = state.servers[state.selected]
    draw_text(screen, "TERMINAL DE AUDITORIA", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)

    dots = "." * (1 + int(state.connect_timer * 4) % 3)
    draw_text(screen, f"CONECTANDO A {srv['id']}{dots}", font_body, NEON_YELLOW, panel.x + 20, panel.y + 90)

    bar_x, bar_y, bar_w, bar_h = panel.x + 20, panel.y + 130, panel.width - 40, 18
    pygame.draw.rect(screen, (25, 25, 25), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
    prog = min(1.0, state.connect_timer / CONNECT_TIME)
    pygame.draw.rect(screen, NEON_CYAN, (bar_x, bar_y, int(bar_w * prog), bar_h), border_radius=6)
    pygame.draw.rect(screen, NEON_CYAN, (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=6)


def draw_terminal_analyzing(panel):
    srv = state.servers[state.selected]
    draw_text(screen, f"TERMINAL DE AUDITORIA -- {srv['id']}", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)

    full = state.log_tw.full_text
    visible = full[:state.log_tw.visible_len()]
    lines = visible.split("\n")

    y = panel.y + 58
    for line in lines:
        if line.startswith("[PISTA]") or line.startswith("        "):
            color = NEON_YELLOW
        elif line.startswith("[AUDITORIA]"):
            color = NEON_PURPLE
        elif line.strip().startswith(("#", "--")):
            color = NEON_CYAN
        elif line.strip() == "":
            color = TEXT_DIM
        else:
            color = NEON_GREEN
        draw_text(screen, line, font_code, color, panel.x + 22, y)
        y += 21

    if not state.log_tw.done() and int(pygame.time.get_ticks() / 300) % 2 == 0:
        draw_text(screen, "_", font_code, NEON_GREEN, panel.x + 22, y)

    draw_text(screen, "Classifique o gatilho identificado:", font_body, TEXT_MAIN,
              panel.x + 20, panel.bottom - 130)

    buttons = diagnosis_button_rects(panel)
    labels = {"LOGICA": "BOMBA LOGICA (gatilho de estado)", "RELOGIO": "BOMBA RELOGIO (gatilho temporal)"}
    colors = {"LOGICA": NEON_PINK, "RELOGIO": NEON_CYAN}
    for kind, rect in buttons.items():
        neon_panel(rect, colors[kind], bg_color=(16, 18, 26), width=3, radius=8)
        draw_text(screen, labels[kind], font_body, colors[kind], rect.centerx, rect.centery, center=True)


def draw_terminal_feedback(panel):
    srv = state.servers[state.selected]
    color = NEON_GREEN if state.last_correct else NEON_RED
    title = "DIAGNOSTICO CORRETO -- AMEACA NEUTRALIZADA" if state.last_correct else "DIAGNOSTICO INCORRETO -- INTEGRIDADE REDUZIDA"
    draw_text(screen, f"TERMINAL DE AUDITORIA -- {srv['id']}", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)

    draw_text(screen, title, font_body, color, panel.x + 20, panel.y + 66)
    y = panel.y + 100
    for line in wrap_text(state.last_explain, font_body, panel.width - 44):
        draw_text(screen, line, font_body, TEXT_MAIN, panel.x + 22, y)
        y += 25

    draw_text(screen, f"Retornando a lista de servidores em {max(0, state.feedback_timer):.1f}s...",
              font_small, TEXT_DIM, panel.x + 20, panel.bottom - 30)


def draw_hub_or_playing():
    draw_background()
    if state.glitch_timer > 0:
        glitch = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        glitch.fill((255, 0, 60, 25))
        screen.blit(glitch, (random.randint(-6, 6), random.randint(-4, 4)))

    draw_server_list()

    panel = pygame.Rect(368, 128, WIDTH - 388, HEIGHT - 160)
    neon_panel(panel, NEON_CYAN, bg_color=TERMINAL_BG)

    if state.status == "hub":
        draw_terminal_idle(panel)
    elif state.status == "connecting":
        draw_terminal_connecting(panel)
    elif state.status == "analyzing":
        draw_terminal_analyzing(panel)
    elif state.status == "feedback":
        draw_terminal_feedback(panel)

    draw_hud()
    draw_text(screen, "ESC para sair", font_small, TEXT_DIM, WIDTH // 2, HEIGHT - 14, center=True)


# ---------------------------------------------------------------------------
# Boot / telas finais
# ---------------------------------------------------------------------------
def draw_boot():
    screen.fill(BG)
    rain.update_and_draw(screen, alpha=70)
    draw_text(screen, "TECHSECURE S.A. -- NUCLEO DE SEGURANCA", font_title, NEON_GREEN, WIDTH // 2, 200, center=True)

    y = 280
    for i in range(min(state.boot_index, len(BOOT_LINES))):
        draw_text(screen, f"> {BOOT_LINES[i]}", font_body, NEON_GREEN, WIDTH // 2 - 320, y)
        y += 34

    if state.boot_index >= len(BOOT_LINES):
        if int(pygame.time.get_ticks() / 400) % 2 == 0:
            draw_text(screen, "PRESSIONE ESPACO PARA INICIAR A AUDITORIA", font_h2, NEON_YELLOW,
                      WIDTH // 2, y + 40, center=True)


def draw_end_screen():
    draw_background()
    victory = state.status == "victory"
    title = "TODOS OS SERVIDORES NEUTRALIZADOS" if victory else "PROTOCOLO DE EMERGENCIA ACIONADO"
    sub = "A rede corporativa foi protegida a tempo." if victory else (
        "Tempo esgotado ou integridade da rede zerada." if not victory else "")
    color = NEON_GREEN if victory else NEON_RED

    draw_text(screen, title, font_title, color, WIDTH // 2, 130, center=True)
    draw_text(screen, sub, font_body, TEXT_DIM, WIDTH // 2, 168, center=True)

    draw_text(screen, f"Servidores neutralizados: {state.secured_count()}/{len(state.servers)}",
              font_h2, NEON_YELLOW, WIDTH // 2, 220, center=True)
    draw_text(screen, f"Falhas de diagnostico: {state.mistakes}", font_body, TEXT_MAIN,
              WIDTH // 2, 252, center=True)
    draw_text(screen, f"Integridade final: {max(0, state.integrity)}%", font_body, TEXT_MAIN,
              WIDTH // 2, 278, center=True)

    panel = pygame.Rect(120, 320, WIDTH - 240, 320)
    neon_panel(panel, NEON_CYAN)
    draw_text(screen, "RESUMO TECNICO DOS INCIDENTES:", font_body, TEXT_MAIN, panel.x + 20, panel.y + 16)
    y = panel.y + 50
    for srv in state.servers:
        result = "NEUTRALIZADO" if srv["state"] == "secured" else "NAO RESOLVIDO"
        rcolor = NEON_GREEN if srv["state"] == "secured" else NEON_RED
        draw_text(screen, f"{srv['id']} ({srv['label']}) -- {result}", font_small, rcolor, panel.x + 20, y)
        y += 24
        tipo = "Bomba Logica (gatilho de estado)" if srv["type"] == "LOGICA" else "Bomba Relogio (gatilho temporal)"
        draw_text(screen, f"   Classificacao correta: {tipo}", font_small, TEXT_DIM, panel.x + 20, y)
        y += 30

    draw_text(screen, "Pressione R para reiniciar  |  ESC para sair", font_small, TEXT_DIM,
              WIDTH // 2, HEIGHT - 25, center=True)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
def main():
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and state.status == "boot" and state.boot_index >= len(BOOT_LINES):
                    state.status = "hub"
                elif event.key == pygame.K_r and state.status in ("gameover", "victory"):
                    state.reset()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.status == "hub":
                    panel = pygame.Rect(20, 128, 330, HEIGHT - 160)
                    y = panel.y + 58
                    card_h = 110
                    for i in range(len(state.servers)):
                        rect = pygame.Rect(panel.x + 14, y, panel.width - 28, card_h)
                        if rect.collidepoint(event.pos) and state.servers[i]["state"] != "secured":
                            state.select_server(i)
                            break
                        y += card_h + 14
                elif state.status == "analyzing":
                    panel = pygame.Rect(368, 128, WIDTH - 388, HEIGHT - 160)
                    for kind, rect in diagnosis_button_rects(panel).items():
                        if rect.collidepoint(event.pos):
                            state.submit_diagnosis(kind)
                            break

        state.update(dt)

        if state.status == "boot":
            draw_boot()
        elif state.status in ("hub", "connecting", "analyzing", "feedback"):
            draw_hub_or_playing()
        elif state.status in ("gameover", "victory"):
            draw_end_screen()

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()