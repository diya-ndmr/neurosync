import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Compass, Home, ArrowLeft } from 'lucide-react';
import NeoButton from '../components/Buttons/NeoButton';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="login-stage min-h-screen flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center max-w-md"
      >
        <div className="neo-card p-10 flex flex-col items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-brand-100 flex items-center justify-center">
            <Compass size={40} className="text-brand-600" />
          </div>
          <div>
            <h1 className="text-6xl font-extrabold text-ink tracking-tight">404</h1>
            <p className="mt-2 text-ink-soft font-medium">This path has drifted off the neural network.</p>
          </div>
          <div className="flex gap-3">
            <NeoButton variant="secondary" onClick={() => navigate(-1)}>
              <ArrowLeft size={16} className="inline mr-1" />
              Go Back
            </NeoButton>
            <NeoButton onClick={() => navigate('/')}>
              <Home size={16} className="inline mr-1" />
              Home
            </NeoButton>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
