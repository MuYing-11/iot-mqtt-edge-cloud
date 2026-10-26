import "./globals.css";
import LiveProvider from "@/components/LiveProvider";
import Nav from "@/components/Nav";

export const metadata = {
  title: "IoT Cloud Dashboard",
  description: "Live data from the Raspberry Pi edge node, received by the EC2 MQTT broker",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <LiveProvider>
          <Nav />
          <main>{children}</main>
          <footer>RT5 INSAT · Technologies et Protocoles pour l&apos;IoT · TP1 + TP2 · Sensors → Raspberry Pi (edge) → EC2 (cloud)</footer>
        </LiveProvider>
      </body>
    </html>
  );
}
