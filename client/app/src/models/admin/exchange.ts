/**
 * Exchange established between two sites of the platform.
 *
 * The type says what the two sites exchange - a transmission files on the other
 * site a report composed here, a communication carries to it what a report of
 * this site holds - and the mode what the two sides are: each of them names a
 * site or a profile, by its UUID, and a side naming a profile stands for every
 * site that inherits from it.
 *
 * Every exchange runs through a channel of its destination: one of the
 * channels of it that the exchanges run through, chosen among them when the
 * exchange is established or declared there by naming it, and never named
 * again. The channel carries the name the exchange is known by on that side
 * and the recipients that take part in it, and is configured on the site
 * holding it by the administrators of the platform.
 *
 * The owner is the side the report the exchange creates belongs to, and what
 * the exchange is decides it: a transmission files on the destination, that
 * owns what it receives; a communication carries what a report of the sender
 * holds, and stays the sender's. What a site owns lives on it, composed with
 * the questionnaire the exchange names; of the channel of the destination
 * only the recipients take part where the report is not theirs.
 */
export type exchangeType = "transmission" | "communication";

export type exchangeOwner = "source" | "target";

export type exchangeMode = "site-site" | "profile-site" | "site-profile" | "profile-profile";

export interface exchangeModel {
  id: string;
  type: exchangeType;
  mode: exchangeMode;
  source: string;
  target: string;
  owner: exchangeOwner;
  channel: string;
  questionnaire: string;
  request_questionnaire: string;
  channel_name: string;
}

export interface exchangeConfig {
  questionnaire: string;
  request_questionnaire: string;
}

export const exchangeTypeLabels: Record<exchangeType, string> = {
  transmission: "Transmission",
  communication: "Communication"
};

/**
 * The two sides a mode is made of. The label of a mode is composed from them
 * at rendering time, so that what reaches the translators is the name of the
 * two objects and not the four combinations they can be arranged in.
 */
export const exchangeModeSides: Record<exchangeMode, [string, string]> = {
  "site-site": ["Site", "Site"],
  "profile-site": ["Profile", "Site"],
  "site-profile": ["Site", "Profile"],
  "profile-profile": ["Profile", "Profile"]
};
