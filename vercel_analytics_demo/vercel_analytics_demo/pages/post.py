"""A dynamic route: the page view carries the template /post/[pid], not the concrete id."""

from __future__ import annotations

import reflex as rx

from ..layout import page_shell, section


class PostState(rx.State):
    @rx.var
    def pid(self) -> str:
        return self.router.url.path.rsplit("/", 1)[-1]


def post() -> rx.Component:
    return page_shell(
        "Dynamic route",
        "Reflex dynamic routes ([pid]) become React Router params; the bridge turns them back into "
        "the route template Vercel groups page views by.",
        section(
            "This post",
            rx.text("pid: ", rx.code(PostState.pid), size="3"),
            rx.hstack(
                *[rx.link(f"/post/{pid}", href=f"/post/{pid}", size="2") for pid in (1, 42, 777)],
                spacing="4",
            ),
            rx.text(
                "Every one of these links reports path /post/<id> with route /post/[pid].",
                size="2",
                color=rx.color("gray", 11),
            ),
            icon="file-text",
        ),
    )


rx.page(route="/post/[pid]", title="Post | Vercel Analytics demo")(post)
