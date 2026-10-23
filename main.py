import random
import flet as ft

CARD_WIDTH = 84
CARD_HEIGHT = 120
CARD_OFFSET_DOWN = 18
CARD_OFFSET_UP = 27
DROP_PROXIMITY = 40
BOARD_WIDTH = 800
BOARD_HEIGHT = 650

# Use None para um fundo vermelho.
# Para usar uma imagem, coloque-a em assets/images e informe o caminho abaixo.
BACKGROUND_IMAGE = "images/papel de parede solitário.jpg"

# O projeto já contém images/card_back.png.
# Troque pelo nome do seu arquivo personalizado se quiser outro verso.
CARD_BACK_IMAGE = "images/fundo de cartas.jpg"


class Suite:
    def __init__(self, name, color):
        self.name = name
        self.color = color


class Rank:
    def __init__(self, name, value):
        self.name = name
        self.value = value


def main(page: ft.Page):
    page.title = "Solitaire"
    page.padding = 0
    page.bgcolor = "#8B0000"

    # O tabuleiro ocupa a janela; as cartas são redimensionadas mantendo
    # a proporção do layout original.
    current_scale = 1.0
    offset_x = 0.0
    offset_y = 0.0

    background_view = ft.Container(
        width=BOARD_WIDTH,
        height=BOARD_HEIGHT,
        bgcolor=page.bgcolor,
        image=(
            ft.DecorationImage(
                src=BACKGROUND_IMAGE,
                fit=ft.BoxFit.COVER,
            )
            if BACKGROUND_IMAGE
            else None
        ),
        ignore_interactions=True,
    )

    board = ft.Stack(
        controls=[background_view],
        width=BOARD_WIDTH,
        height=BOARD_HEIGHT,
    )

    slots = []

    def make_slot(name, left, top, pile_offset=0):
        view = ft.Container(
            width=CARD_WIDTH,
            height=CARD_HEIGHT,
            left=left,
            top=top,
            border=ft.Border.all(1, "#DDDDDD"),
            border_radius=6,
            bgcolor="#33000000",
        )

        slot = {
            "name": name,
            "left": left,
            "top": top,
            "view": view,
            "cards": [],
            "pile_offset": pile_offset,
        }
        slots.append(slot)
        board.controls.append(view)
        return slot

    stock = make_slot("stock", 0, 0)
    waste = make_slot("waste", 90, 0)

    foundations = [
        make_slot(f"foundation_{i}", 360 + i * 90, 0)
        for i in range(4)
    ]

    tableau = [
        make_slot(
            f"tableau_{i}",
            i * 100,
            140,
            pile_offset=16,
        )
        for i in range(7)
    ]

    class Card(ft.GestureDetector):
        def __init__(self, suite, rank):
            super().__init__()

            self.suite = suite
            self.rank = rank
            self.face_up = False
            self.slot = None
            self.drag_pile = []

            self.mouse_cursor = ft.MouseCursor.MOVE
            self.drag_interval = 5
            self.on_pan_start = self.start_drag
            self.on_pan_update = self.drag
            self.on_pan_end = self.end_drag
            self.on_tap = self.tap

            self.image = ft.Image(
                src=CARD_BACK_IMAGE,
                width=CARD_WIDTH,
                height=CARD_HEIGHT,
                fit=ft.BoxFit.FILL,
            )

            self.content = ft.Container(
                width=CARD_WIDTH,
                height=CARD_HEIGHT,
                border=ft.Border.all(1, "#222222"),
                border_radius=6,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=self.image,
            )

        def tap(self, e):
            # As cartas do estoque cobrem o espaço; o clique no topo compra uma carta.
            if self.slot is stock and stock["cards"] and stock["cards"][-1] is self:
                draw_from_stock(e)

        def set_face_up(self, face_up):
            self.face_up = face_up

            if face_up:
                self.image.src = (
                    f"images/{self.rank.name}_{self.suite.name}.svg"
                )
            else:
                self.image.src = CARD_BACK_IMAGE

        def start_drag(self, e: ft.DragStartEvent):
            if not self.face_up or self.slot is None:
                return

            source_cards = self.slot["cards"]
            start_index = source_cards.index(self)

            # No tableau, arrasta junto esta carta e as que estão acima dela.
            if self.slot["name"].startswith("tableau"):
                self.drag_pile = source_cards[start_index:]
            else:
                # No waste/fundação, só a carta do topo pode ser movida.
                self.drag_pile = [self]

            for card in self.drag_pile:
                if card in board.controls:
                    board.controls.remove(card)
                board.controls.append(card)

            board.update()

        def drag(self, e: ft.DragUpdateEvent):
            if not self.drag_pile:
                return

            self.left = max(0, self.left + e.local_delta.x)
            self.top = max(0, self.top + e.local_delta.y)

            for index, card in enumerate(self.drag_pile[1:], start=1):
                card.left = self.left
                card.top = self.top + index * CARD_OFFSET_UP * current_scale

            board.update()

        def can_drop_on(self, slot):
            moving_card = self.drag_pile[0]

            if slot["name"].startswith("tableau"):
                if not slot["cards"]:
                    return moving_card.rank.value == 13

                target_card = slot["cards"][-1]
                return (
                    target_card.face_up
                    and target_card.rank.value == moving_card.rank.value + 1
                    and target_card.suite.color != moving_card.suite.color
                )

            if slot["name"].startswith("foundation"):
                if len(self.drag_pile) != 1:
                    return False

                if not slot["cards"]:
                    return moving_card.rank.value == 1

                target_card = slot["cards"][-1]
                return (
                    target_card.suite.name == moving_card.suite.name
                    and moving_card.rank.value == target_card.rank.value + 1
                )

            return False

        def end_drag(self, e: ft.DragEndEvent):
            if not self.drag_pile:
                return

            destination = None
            tolerance = DROP_PROXIMITY * current_scale

            for slot in tableau + foundations:
                if slot is self.slot:
                    continue

                target_left = offset_x + slot["left"] * current_scale
                target_top = offset_y + slot["top"] * current_scale

                if slot["name"].startswith("tableau") and slot["cards"]:
                    target_card = slot["cards"][-1]
                    target_left = target_card.left
                    target_top = target_card.top

                    is_over_target = (
                        abs(self.left - target_left) < tolerance
                        and target_top - tolerance
                        <= self.top
                        <= target_top + CARD_HEIGHT * current_scale
                    )
                else:
                    is_over_target = (
                        abs(self.left - target_left) < tolerance
                        and abs(self.top - target_top) < tolerance
                    )

                if is_over_target and self.can_drop_on(slot):
                    destination = slot
                    break

            if destination is None:
                update_positions()
                self.drag_pile = []
                return

            source = self.slot
            first_card_index = source["cards"].index(self)
            moving_cards = source["cards"][first_card_index:]

            del source["cards"][first_card_index:]
            destination["cards"].extend(moving_cards)

            for card in moving_cards:
                card.slot = destination

            # Vira para cima a nova carta exposta na coluna de origem.
            if source["name"].startswith("tableau") and source["cards"]:
                source["cards"][-1].set_face_up(True)

            update_positions()
            self.drag_pile = []

    suites = [
        Suite("hearts", "RED"),
        Suite("diamonds", "RED"),
        Suite("clubs", "BLACK"),
        Suite("spades", "BLACK"),
    ]

    ranks = [
        Rank("Ace", 1),
        Rank("2", 2),
        Rank("3", 3),
        Rank("4", 4),
        Rank("5", 5),
        Rank("6", 6),
        Rank("7", 7),
        Rank("8", 8),
        Rank("9", 9),
        Rank("10", 10),
        Rank("Jack", 11),
        Rank("Queen", 12),
        Rank("King", 13),
    ]

    cards = [Card(suite, rank) for suite in suites for rank in ranks]
    random.shuffle(cards)

    def update_positions():
        for slot in slots:
            card_top = offset_y + slot["top"] * current_scale

            for card in slot["cards"]:
                card.slot = slot
                card.left = offset_x + slot["left"] * current_scale
                card.top = card_top

                if slot["name"].startswith("tableau"):
                    offset = (
                        CARD_OFFSET_UP
                        if card.face_up
                        else CARD_OFFSET_DOWN
                    )
                    card_top += offset * current_scale

        board.update()

    # Distribui uma carta a mais em cada coluna do tableau.
    card_index = 0

    for column_index, slot in enumerate(tableau):
        for row_index in range(column_index + 1):
            card = cards[card_index]
            card_index += 1
            card.slot = slot
            card.set_face_up(row_index == column_index)
            slot["cards"].append(card)
            board.controls.append(card)

    # As cartas restantes começam viradas para baixo no monte de compra.
    for card in cards[card_index:]:
        card.slot = stock
        card.set_face_up(False)
        stock["cards"].append(card)
        board.controls.append(card)

    def draw_from_stock(e):
        # Move uma carta do estoque para o descarte à direita.
        # Quando o estoque acabar, ele permanece vazio.
        if not stock["cards"]:
            return

        card = stock["cards"].pop()
        card.slot = waste
        card.set_face_up(True)
        waste["cards"].append(card)
        board.controls.remove(card)
        board.controls.append(card)

        update_positions()

    stock["view"].on_click = draw_from_stock

    # Define as posições iniciais antes de adicionar o jogo à página.
    for slot in slots:
        for index, card in enumerate(slot["cards"]):
            card.left = slot["left"]
            if slot["name"].startswith("tableau"):
                offset = CARD_OFFSET_UP if card.face_up else CARD_OFFSET_DOWN
                card.top = slot["top"] + index * offset
            else:
                card.top = slot["top"]

    def apply_responsive_layout(e=None):
        nonlocal current_scale, offset_x, offset_y

        viewport_width = page.width or BOARD_WIDTH
        viewport_height = page.height or BOARD_HEIGHT

        current_scale = min(
            viewport_width / BOARD_WIDTH,
            viewport_height / BOARD_HEIGHT,
        )
        current_scale = max(0.1, current_scale)

        scaled_width = BOARD_WIDTH * current_scale
        scaled_height = BOARD_HEIGHT * current_scale
        offset_x = (viewport_width - scaled_width) / 2
        offset_y = (viewport_height - scaled_height) / 2

        board.width = viewport_width
        board.height = viewport_height

        background_view.width = viewport_width
        background_view.height = viewport_height

        scaled_card_width = CARD_WIDTH * current_scale
        scaled_card_height = CARD_HEIGHT * current_scale

        for slot in slots:
            slot["view"].width = scaled_card_width
            slot["view"].height = scaled_card_height
            slot["view"].left = offset_x + slot["left"] * current_scale
            slot["view"].top = offset_y + slot["top"] * current_scale

        for card in cards:
            card.width = scaled_card_width
            card.height = scaled_card_height
            card.content.width = scaled_card_width
            card.content.height = scaled_card_height
            card.image.width = scaled_card_width
            card.image.height = scaled_card_height

        update_positions()

    page.on_resize = apply_responsive_layout
    page.add(board)
    apply_responsive_layout()


ft.run(main, assets_dir="assets")









