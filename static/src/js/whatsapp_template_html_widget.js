import { HtmlField, htmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";

// You may need to import your dynamic placeholder plugins here
// import { DYNAMIC_PLACEHOLDER_PLUGINS } from "path/to/your/plugins";

export class WhatsAppTemplateHtmlWidget extends HtmlField {
    setup() {
        super.setup();
        this.orm = useService ? useService("orm") : null;
        useEffect(() => {
            // Optionally, you can trigger something after mount
        });
    }

    getConfig() {
        const config = super.getConfig();
        // Only allow emoji and dynamic placeholder plugins
        config.toolbar = [
            "emoji", // Only emoji button
            // Add any other minimal tools you want, e.g. "undo", "redo"
        ];
        config.plugins = [
            ...(typeof DYNAMIC_PLACEHOLDER_PLUGINS !== "undefined" ? DYNAMIC_PLACEHOLDER_PLUGINS : []),
            "emoji",
        ];
        config.allowedTags = []; // No HTML tags allowed
        config.allowedStyles = [];
        config.allowedAttributes = {};
        config.codeview = false; // Disable codeview
        config.placeholder = "Type your WhatsApp message, use emojis and dynamic fields...";
        return config;
    }
}

export const whatsappTemplateHtmlWidget = {
    ...htmlField,
    component: WhatsAppTemplateHtmlWidget,
};

registry.category("fields").add("html_whatsapp", whatsappTemplateHtmlWidget);
