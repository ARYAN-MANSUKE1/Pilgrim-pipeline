<?php
/**
 * Theme footer.
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$primary_nav = pds_get_primary_menu();
$footer_bg   = PDS_URI . '/assets/images/Footer-BG.png';
$email       = 'pilgrimdataservices@gmail.com';
$year        = gmdate( 'Y' );

$social_links = array(
	array( 'url' => '#', 'icon' => 'fa-instagram', 'label' => 'instagram' ),
	array( 'url' => '#', 'icon' => 'fa-facebook', 'label' => 'facebook' ),
	array( 'url' => '#', 'icon' => 'fa-youtube-play', 'label' => 'youtube' ),
);

$legal_links = array(
	array( 'url' => '#', 'label' => 'privacy' ),
	array( 'url' => '#', 'label' => 'terms' ),
);
?>
<footer
	id="site-footer"
	class="site-footer pds-footer"
	style="background-image: url('<?php echo esc_url( $footer_bg ); ?>');"
>
	<div class="footer-inner">
		<?php if ( $primary_nav ) : ?>
			<nav class="footer-nav footer-nav--primary" aria-label="<?php esc_attr_e( 'Footer primary', 'pilgrim-data-services' ); ?>">
				<?php echo $primary_nav; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
			</nav>
		<?php endif; ?>

		<nav class="footer-nav footer-nav--legal" aria-label="<?php esc_attr_e( 'Footer legal', 'pilgrim-data-services' ); ?>">
			<ul class="menu">
				<?php foreach ( $legal_links as $legal ) : ?>
					<li>
						<a href="<?php echo esc_url( $legal['url'] ); ?>">
							<?php echo pds_lang_blocks( $legal['label'] ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
						</a>
					</li>
				<?php endforeach; ?>
			</ul>
		</nav>

		<div class="footer-meta">
			<div class="footer-social">
				<?php foreach ( $social_links as $social ) : ?>
					<a href="<?php echo esc_url( $social['url'] ); ?>"<?php echo '#' !== $social['url'] ? ' target="_blank" rel="noopener noreferrer"' : ''; ?>>
						<i class="fa <?php echo esc_attr( $social['icon'] ); ?>" aria-hidden="true"></i>
						<?php echo pds_lang_blocks( $social['label'] ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
					</a>
				<?php endforeach; ?>
			</div>
			<div class="footer-email">
				<a href="<?php echo esc_url( 'mailto:' . $email ); ?>">
					<i class="fa fa-envelope" aria-hidden="true"></i>
					<span><?php echo esc_html( $email ); ?></span>
				</a>
			</div>
		</div>

		<div class="footer-copy">
			<hr class="footer-divider" aria-hidden="true">
			<div class="copyright">
				<?php foreach ( array_keys( pds_get_temple_languages() ) as $pds_code ) : ?>
					<p class="<?php echo esc_attr( $pds_code ); ?>_lang dis_lang" style="display: <?php echo 'mr' === $pds_code ? 'block' : 'none'; ?>;">@<?php echo esc_html( $year ); ?> <?php echo esc_html( pds_t( 'rights', $pds_code ) ); ?></p>
				<?php endforeach; ?>
			</div>
		</div>
	</div>
</footer>

<?php
get_template_part( 'template-parts/temple-popup' );
wp_footer();
?>
</body>
</html>
