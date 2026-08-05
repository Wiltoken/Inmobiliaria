import { useState, useEffect, useCallback } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

export default function PhotoGallery({ photos = [], title = '' }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showLightbox, setShowLightbox] = useState(false);

  // Default placeholder if no photos
  const allPhotos = photos.length > 0
    ? photos
    : [{ id: 'default', url: 'https://picsum.photos/800/600', order: 0 }];

  const goToNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % allPhotos.length);
  }, [allPhotos.length]);

  const goToPrev = useCallback(() => {
    setCurrentIndex((prev) => (prev - 1 + allPhotos.length) % allPhotos.length);
  }, [allPhotos.length]);

  // Keyboard navigation
  useEffect(() => {
    if (!showLightbox) return;

    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight') goToNext();
      if (e.key === 'ArrowLeft') goToPrev();
      if (e.key === 'Escape') setShowLightbox(false);
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showLightbox, goToNext, goToPrev]);

  // Prevent body scroll when lightbox is open
  useEffect(() => {
    if (showLightbox) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [showLightbox]);

  return (
    <>
      {/* Main Gallery */}
      <div className="relative bg-gray-100 rounded-xl overflow-hidden">
        {/* Main Image */}
        <div
          className="aspect-[4/3] cursor-pointer gallery-container"
          onClick={() => setShowLightbox(true)}
        >
          <img
            src={allPhotos[currentIndex]?.url}
            alt={`${title} - Foto ${currentIndex + 1}`}
            className="w-full h-full object-cover"
          />
        </div>

        {/* Navigation Arrows */}
        {allPhotos.length > 1 && (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation();
                goToPrev();
              }}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full
                       bg-white/90 hover:bg-white shadow-lg flex items-center justify-center
                       transition-colors"
              aria-label="Foto anterior"
            >
              <ChevronLeft className="w-6 h-6 text-gray-700" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                goToNext();
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full
                       bg-white/90 hover:bg-white shadow-lg flex items-center justify-center
                       transition-colors"
              aria-label="Foto siguiente"
            >
              <ChevronRight className="w-6 h-6 text-gray-700" />
            </button>
          </>
        )}

        {/* Photo Counter */}
        {allPhotos.length > 1 && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-3 py-1
                        bg-black/60 text-white text-sm rounded-full">
            {currentIndex + 1} / {allPhotos.length}
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {allPhotos.length > 1 && (
        <div className="flex gap-2 mt-3 overflow-x-auto scrollbar-hide pb-2">
          {allPhotos.map((photo, index) => (
            <button
              key={photo.id || index}
              onClick={() => setCurrentIndex(index)}
              className={`
                flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all
                ${index === currentIndex
                  ? 'border-primary'
                  : 'border-transparent hover:border-gray-300'
                }
              `}
            >
              <img
                src={photo.url}
                alt={`Miniatura ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      )}

      {/* Lightbox */}
      {showLightbox && (
        <div
          className="fixed inset-0 z-50 bg-black flex items-center justify-center"
          onClick={() => setShowLightbox(false)}
        >
          {/* Close Button */}
          <button
            onClick={() => setShowLightbox(false)}
            className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10
                     hover:bg-white/20 flex items-center justify-center transition-colors"
            aria-label="Cerrar"
          >
            <X className="w-6 h-6 text-white" />
          </button>

          {/* Image */}
          <img
            src={allPhotos[currentIndex]?.url}
            alt={`${title} - Foto ${currentIndex + 1}`}
            className="max-w-full max-h-[90vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />

          {/* Navigation */}
          {allPhotos.length > 1 && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  goToPrev();
                }}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                         bg-white/10 hover:bg-white/20 flex items-center justify-center
                         transition-colors"
                aria-label="Foto anterior"
              >
                <ChevronLeft className="w-8 h-8 text-white" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  goToNext();
                }}
                className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                         bg-white/10 hover:bg-white/20 flex items-center justify-center
                         transition-colors"
                aria-label="Foto siguiente"
              >
                <ChevronRight className="w-8 h-8 text-white" />
              </button>
            </>
          )}

          {/* Counter */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2
                        bg-white/10 text-white text-sm rounded-full">
            {currentIndex + 1} / {allPhotos.length}
          </div>
        </div>
      )}
    </>
  );
}
