from django.urls import reverse


class InclusionsMixin:
    def assertResponseData(self, url_name, expected, params=None, **url_kwargs):
        url = reverse(url_name, kwargs=url_kwargs)

        response = self.client.get(url, data=params)

        self.assertEqual(response.json(), expected)
