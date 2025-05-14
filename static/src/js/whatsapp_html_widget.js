import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

export class WhatsAppHtmlWidget extends HtmlField {
    setup() {
        super.setup();
        this.orm = useService ? useService("orm") : null;
        onMounted(() => {
            // Only show dynamic placeholder if model_id is set
            if (
                this.props.options &&
                this.props.options.dynamic_placeholder &&
                this.orm &&
                this.props.record &&
                this.props.record.data.model_id &&
                this.props.record.data.model_id[0]
            ) {
                this.addDynamicPlaceholderButton();
            }
        });
    }

    async addDynamicPlaceholderButton() {
        const modelId = this.props.record.data.model_id[0];
        if (!modelId) return;
        const [model] = await this.orm.call("ir.model", "read", [modelId], ["model"]);
        if (!model) return;
        const fields = await this.orm.call(model.model, "fields_get", [], {});
        // Wait for the editor to be available in the DOM
        await this.editor?.whenReady?.();
        const $toolbar = this.el.querySelector(".o_html_field_toolbar");
        if (!$toolbar) return;
        // Remove existing dropdown if any
        const oldDropdown = $toolbar.querySelector(".o_whatsapp_placeholder_dropdown");
        if (oldDropdown) oldDropdown.remove();
        const $dropdown = document.createElement("select");
        $dropdown.className = "o_whatsapp_placeholder_dropdown";
        $dropdown.innerHTML = `<option value="">Insert Field...</option>` +
            Object.keys(fields).map(f => `<option value="${f}">${fields[f].string || f}</option>`).join("");
        $dropdown.onchange = () => {
            if ($dropdown.value) {
                this.editor.execCommand("insertText", { text: `{{ ${$dropdown.value} }}` });
                $dropdown.value = "";
            }
        };
        $toolbar.appendChild($dropdown);
    }

    getConfig() {
        const config = super.getConfig();
        config.toolbar = ["emoji"];
        config.plugins = ["emoji"];
        config.allowedTags = [];
        config.allowedStyles = [];
        config.allowedAttributes = {};
        config.codeview = !!(this.props.options && this.props.options.codeview);
        config.placeholder = "Type your WhatsApp message, use emojis and dynamic fields...";
        return config;
    }
}

export const whatsappHtmlWidget = {
    ...htmlField,
    component: WhatsAppHtmlWidget,
};

registry.category("fields").add("whatsapp_html", whatsappHtmlWidget);
