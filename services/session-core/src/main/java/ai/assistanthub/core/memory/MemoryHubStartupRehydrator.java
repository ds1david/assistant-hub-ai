package ai.assistanthub.core.memory;

import ai.assistanthub.core.session.ConversationSession;
import ai.assistanthub.core.session.SessionRepository;
import ai.assistanthub.sdk.HubEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Na subida do processo, popula o cache em memória de {@link SessionRepository} a partir do
 * SQLite do Memory Hub (issue #29 / R3) — sem isso, sessões/eventos persistidos ficariam
 * invisíveis às leituras (que continuam servidas pelo cache). Antes de repovoar o cache, aplica
 * a política de retenção (expurgo de sessões `ENDED` além do limite configurado), para nunca
 * carregar em memória uma sessão que já seria elegível para expurgo.
 */
@Component
@Order(0)
public class MemoryHubStartupRehydrator implements ApplicationRunner {

    private static final Logger LOGGER = LoggerFactory.getLogger(MemoryHubStartupRehydrator.class);

    private final SessionPersistenceStore persistenceStore;
    private final SessionRepository sessionRepository;
    private final RetentionPolicy retentionPolicy;

    public MemoryHubStartupRehydrator(
            SessionPersistenceStore persistenceStore,
            SessionRepository sessionRepository,
            RetentionPolicy retentionPolicy) {
        this.persistenceStore = persistenceStore;
        this.sessionRepository = sessionRepository;
        this.retentionPolicy = retentionPolicy;
    }

    @Override
    public void run(ApplicationArguments args) {
        int purged = retentionPolicy.purgeExpired();
        if (purged > 0) {
            LOGGER.info("Memory Hub: {} sessão(ões) expurgada(s) por retenção antes da rehydration", purged);
        }

        List<ConversationSession> sessions = persistenceStore.findAllSessions();
        for (ConversationSession session : sessions) {
            List<HubEvent> events = persistenceStore.findEvents(session.id());
            sessionRepository.hydrate(session, events);
        }
        LOGGER.info("Memory Hub: {} sessão(ões) repovoada(s) em memória na subida do processo", sessions.size());
    }
}
