/** @odoo-module */

import { Discuss } from "@mail/core/public_web/discuss";

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * A lightweight client action that mounts the Discuss OWL component and
 * restores/opens the thread given by action.context.channel_id or
 * action.params.channel_id (or falls back to the usual active_id handling).
 */
export class DiscussClientAction extends Component {
	static components = { Discuss };
	static props = ["*"];
	static template = "wa_conn.DiscussClientAction";

	setup() {
		super.setup();
		this.store = useState(useService("mail.store"));
		onWillStart(() => {
			// avoid blocking rendering with restore promise
			this.restoreDiscussThread(this.props);
		});
		onWillUpdateProps((nextProps) => {
			// avoid blocking rendering with restore promise
			this.restoreDiscussThread(nextProps);
		});
	}

	getActiveId(props) {
		// Support passing a numeric channel_id for convenience.
		const channelId = props.action?.context?.channel_id ?? props.action?.params?.channel_id;
		if (channelId) {
			return `mail.channel_${channelId}`;
		}
		return (
			props.action?.context?.active_id ??
			props.action?.params?.active_id ??
			this.store.Thread.localIdToActiveId(this.store.discuss.thread?.localId) ??
			"mail.box_inbox"
		);
	}

	parseActiveId(rawActiveId) {
		const [model, id] = rawActiveId.split("_");
		if (model === "mail.box") {
			return ["mail.box", id];
		}
		return [model, parseInt(id)];
	}

	async restoreDiscussThread(props) {
		try {
			const rawActiveId = this.getActiveId(props);
			console.debug("wa_conn: restoreDiscussThread rawActiveId=", rawActiveId, "props=", props);
			const [model, id] = this.parseActiveId(rawActiveId);
			console.debug("wa_conn: restoreDiscussThread parsed model=", model, "id=", id);
			let activeThread = await this.store.Thread.getOrFetch({ model, id });
			// fallback: sometimes the store expects the discuss model directly
			if (!activeThread) {
				console.debug("wa_conn: primary getOrFetch returned no thread, trying fallback model 'discuss.channel'");
				activeThread = await this.store.Thread.getOrFetch({ model: 'discuss.channel', id });
			}
			// another fallback: try with mail.channel if model was discuss.channel
			if (!activeThread && model !== 'mail.channel') {
				try {
					console.debug("wa_conn: trying fallback with model 'mail.channel'");
					activeThread = await this.store.Thread.getOrFetch({ model: 'mail.channel', id });
				} catch (err) {
					console.warn('wa_conn: fallback mail.channel failed', err);
				}
			}

			console.debug('wa_conn: activeThread after fetch:', activeThread);
			if (activeThread && activeThread.notEq(this.store.discuss.thread)) {
				if (props.action?.params?.highlight_message_id) {
					activeThread.highlightMessage = props.action.params.highlight_message_id;
					delete props.action.params.highlight_message_id;
				}
				activeThread.setAsDiscussThread(false);
			} else if (!activeThread) {
				console.warn('wa_conn: could not restore discuss thread for', rawActiveId, ' — no thread returned by store');
			}
			this.store.discuss.hasRestoredThread = true;
		} catch (err) {
			console.error('wa_conn: error in restoreDiscussThread', err);
		}
	}
}

registry.category("actions").add("wa_conn.discuss_client_action", DiscussClientAction);