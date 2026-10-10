/* Site settings. Edit these two lines; nothing else needs a build. */
window.SITE_CONFIG = {
  /* Where the sermon audio and the large or broken book files live (see README,
     "Audio and large files"). Empty = keep linking to the old site's download
     URLs, which only works while the old server is up. Example once uploaded:
     "https://github.com/<user>/<repo>/releases/download/media-v1/" */
  MEDIA_BASE: "",

  /* Prayer requests form. Paste the Formspree endpoint id (https://formspree.io/f/<id>).
     Until it is set, the form opens the visitor's mail app addressed to PRAYER_EMAIL. */
  FORMSPREE_ID: "",
  PRAYER_EMAIL: "", /* TODO: the church's address for prayer requests */

  /* Daily readings (katameros / synaxarium) are not static data; the sidebar links here. */
  READINGS_URL: "https://katamars.avabishoy.com/"
};
