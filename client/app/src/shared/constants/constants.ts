export const Constants = {

  emailRegexp: "^[\\w+-.]{1,100}@[\\w+-.]{1,100}\\.[A-Za-z]{2,5}$",
  emailRegexpOrEmpty: /^([\w+-.]){0,100}[\w]{1,100}@([\w+-.]){0,100}[\w]{1,100}$|^$/,
  countryCodeRegexpOrEmpty: "[A-Za-z]{0,2}",
  numberRegexp: /^\d+$/,
  phoneNumberRegexp: /^[+]?[\d]+$/,
  hostnameRegexp: "^(?:[a-zA-Z0-9\\-]+\\.)*[a-zA-Z0-9\\-]+\\.?$",
  httpsRegexp: /^https:\/\/([a-z0-9-]+)\.(.*)$|^$/,
  secureLocalUrlRegexp: /^https:\/\/([a-z0-9-]+)\.(.*)$|^\/(.*)$|^$/,
  uuidRegexp: /^([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$/,
  fiscalCodeRegexp: /^[A-Za-z]{6}[0-9]{2}[A-Za-z]{1}[0-9]{2}[A-Za-z]{1}[0-9]{3}[A-Za-z]{1}$/,
};
