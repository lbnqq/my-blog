from types import MethodType


APP_ORDER = {
    "blog": 10,
    "movies": 20,
    "ratings": 30,
    "recommendations": 40,
    "auth": 50,
}

MODEL_ORDER = {
    "blog": {
        "doubanchartmovie": 10,
        "doubanweeklyreputationmovie": 20,
        "upcomingmovienews": 30,
    },
    "movies": {
        "movie": 10,
    },
    "ratings": {
        "ratingform": 10,
        "userrating": 20,
        "usersession": 30,
    },
    "recommendations": {
        "recommendationfeedback": 10,
        "recommendationresult": 20,
    },
    "auth": {
        "user": 10,
        "group": 20,
    },
}


def ordered_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    app_list = sorted(
        app_dict.values(),
        key=lambda app: (APP_ORDER.get(app["app_label"], 999), app["app_label"]),
    )

    for app in app_list:
        order = MODEL_ORDER.get(app["app_label"], {})
        app["models"].sort(
            key=lambda model: (
                order.get(model["model"]._meta.model_name, 999),
                model["model"]._meta.model_name,
            )
        )

    return app_list


def apply_admin_ordering(admin_site):
    admin_site.get_app_list = MethodType(ordered_app_list, admin_site)
