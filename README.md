A Django email backend for GetResponse.

## Usage

Use it like a standard email backend with an additional feature that allows setting `.tag_id` attribute on an `EmailMessage` instance. The `.from_email` attribute is ignored (see settings instead).

## Settings

* `GETRESPONSE_API_TOKEN`
* `GETRESPONSE_FROM_FIELD_ID`
* `GETRESPONSE_ENDPOINT` — `https://api.getresponse.com/v3/` by default.
