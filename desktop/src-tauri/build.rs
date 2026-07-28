fn main() {
  #[cfg(feature = "desktop-tauri")]
  tauri_build::build()
}
