import reflex as rx

config = rx.Config(
    app_name="vercel_analytics_demo",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="light", accent_color="gray", gray_color="slate", radius="large"),
        ),
    ],
    disable_plugins=[rx.plugins.SitemapPlugin],
)
