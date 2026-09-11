import React from "react";
import { motion } from "framer-motion";
import { useLocation } from "react-router-dom";

const pageVariants = {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -8 },
};

export default function PageTransition({ children }) {
    const location = useLocation();
    return (
        <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.25, ease: [0.2, 0.8, 0.2, 1] }}
        >
            {children}
        </motion.div>
    );
}
