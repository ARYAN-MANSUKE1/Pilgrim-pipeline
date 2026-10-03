<?php
/**
 * Theme header.
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}
?><!doctype html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo( 'charset' ); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<link rel="profile" href="https://gmpg.org/xfn/11">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<a class="skip-link screen-reader-text" href="#content"><?php esc_html_e( 'Skip to content', 'pilgrim-data-services' ); ?></a>

<?php
$header_nav = pds_get_primary_menu();
?>
<header id="site-header" class="site-header pds-header">
	<div class="header-top">
		<div class="header-inner">
			<div class="site-branding">
				<div class="site-logo">
					<?php
					if ( has_custom_logo() ) {
						the_custom_logo();
					} else {
						echo '<a class="site-title-link" href="' . esc_url( home_url( '/' ) ) . '">' . esc_html( get_bloginfo( 'name' ) ) . '</a>';
					}
					?>
				</div>
			</div>
			<div class="main-header-extra-class">
				<?php if ( $header_nav ) : ?>
					<nav class="site-navigation" aria-label="<?php esc_attr_e( 'Primary', 'pilgrim-data-services' ); ?>">
						<?php echo $header_nav; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>					</nav>
				<?php endif; ?>
				<span class="nav-sep" aria-hidden="true">|</span>
				<div class="header-translator">
					<label class="screen-reader-text" for="language-select"><?php esc_html_e( 'Language', 'pilgrim-data-services' ); ?></label>
					<select id="language-select">
						<?php foreach ( pds_get_temple_languages() as $pds_hdr_lang_code => $pds_hdr_lang ) : ?>
							<option value="<?php echo esc_attr( $pds_hdr_lang_code ); ?>"><?php echo esc_html( $pds_hdr_lang['label'] ); ?></option>
						<?php endforeach; ?>
					</select>
				</div>

				<button type="button" class="site-navigation-toggle" aria-expanded="false" aria-controls="mobile-menu">
					<span class="menu-icon" aria-hidden="true">☰</span>
					<span class="screen-reader-text"><?php esc_html_e( 'Menu', 'pilgrim-data-services' ); ?></span>
				</button>

				<nav id="mobile-menu" class="site-navigation-dropdown" hidden>
					<?php echo $header_nav; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
				</nav>
			</div>
		</div>
	</div>
	<div class="header-inner header-bottom">
		<div class="header-search-form">
			<?php
			if ( shortcode_exists( 'dcs_search' ) ) {
				echo do_shortcode( '[dcs_search]' );
			} else {
				echo do_shortcode( '[temple_search_filter]' );
			}
			?>
		</div>
	</div>
</header>
