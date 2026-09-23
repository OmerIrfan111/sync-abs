/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [
      "images.unsplash.com",
      "m.media-amazon.com",
      "i5.walmartimages.com",
      "pisces.bbystatic.com",
      "ssl-product-images.www8-hp.com",
      "i.dell.com",
      "p1-ofp.static.pub",
      "cdn.shopify.com",
      "static.bhphoto.com",
      "media.flixcar.com",
    ],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

module.exports = nextConfig;
