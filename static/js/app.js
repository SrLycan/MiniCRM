import { initDeleteDialog } from "./features/client-delete.js";
import { initClientForm } from "./features/client-form.js";
import { initAmbient } from "./ui/ambient.js";
import { initThemeToggle } from "./ui/theme.js";

initAmbient();
initThemeToggle();
initClientForm();
initDeleteDialog();
