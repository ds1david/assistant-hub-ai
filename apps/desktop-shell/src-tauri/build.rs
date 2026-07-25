// Gera o contexto Tauri (OUT_DIR + assets embutidos) usado por `tauri::generate_context!()`
// em main.rs. Só roda com a feature `gui` — sem isso `cargo test` da lib no WSL/Linux
// (sem WebView2/GTK) quebra com "missing cargo:dev instruction".
fn main() {
    #[cfg(feature = "gui")]
    tauri_build::build();
}
